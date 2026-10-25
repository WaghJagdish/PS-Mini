"""Compare candidate against the persisted incumbent using identical fixed test data."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import joblib
from sklearn.datasets import load_breast_cancer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]


def metrics_for(artifact: dict, config: dict) -> dict:
    data = load_breast_cancer()
    _, X_test, _, y_test = train_test_split(
        data.data, data.target,
        test_size=float(config.get("test_size", 0.2)),
        random_state=int(config.get("random_state", 42)),
        stratify=data.target,
    )
    pred = artifact["model"].predict(X_test)
    return {
        "accuracy": float(accuracy_score(y_test, pred)),
        "f1": float(f1_score(y_test, pred, pos_label=0, zero_division=0)),
        "precision": float(precision_score(y_test, pred, pos_label=0, zero_division=0)),
        "recall": float(recall_score(y_test, pred, pos_label=0, zero_division=0)),
    }


def compare(candidate_path: str, incumbent_path: str, candidate_metrics_path: str, decision_path: str) -> dict:
    candidate = joblib.load(candidate_path)
    saved_metrics = json.loads(Path(candidate_metrics_path).read_text(encoding="utf-8"))
    config = saved_metrics["config"]
    candidate_metrics = metrics_for(candidate, config)
    incumbent_file = Path(incumbent_path)
    if not incumbent_file.exists():
        decision = {"decision": "deploy", "reason": "No incumbent exists; first model is eligible for deployment.", "candidate": candidate_metrics, "incumbent": None}
    else:
        incumbent = joblib.load(incumbent_file)
        incumbent_metrics = metrics_for(incumbent, config)
        primary = config.get("primary_metric", "f1")
        tie = config.get("tie_breaker_metric", "accuracy")
        candidate_key = (candidate_metrics[primary], candidate_metrics[tie])
        incumbent_key = (incumbent_metrics[primary], incumbent_metrics[tie])
        # Strictly better lexicographic score; exact ties retain the deployed model.
        wins = candidate_key > incumbent_key
        decision = {
            "decision": "deploy" if wins else "reject",
            "reason": f"Candidate {'outperforms' if wins else 'does not outperform'} incumbent on {primary}, then {tie}.",
            "primary_metric": primary,
            "tie_breaker_metric": tie,
            "candidate": candidate_metrics,
            "incumbent": incumbent_metrics,
        }
    out = Path(decision_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(decision, indent=2), encoding="utf-8")
    print(json.dumps(decision, indent=2))
    return decision


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", default=str(ROOT / "artifacts/candidate.joblib"))
    parser.add_argument("--incumbent", required=True)
    parser.add_argument("--candidate-metrics", default=str(ROOT / "artifacts/candidate_metrics.json"))
    parser.add_argument("--decision", default=str(ROOT / "artifacts/decision.json"))
    a = parser.parse_args()
    compare(a.candidate, a.incumbent, a.candidate_metrics, a.decision)
