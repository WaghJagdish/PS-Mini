"""Train a candidate Random Forest on the bundled Wisconsin breast-cancer dataset."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import joblib
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "model.json"


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict:
    with open(path, encoding="utf-8") as f:
        config = json.load(f)
    if config.get("primary_metric") not in {"f1", "accuracy"}:
        raise ValueError("primary_metric must be 'f1' or 'accuracy'")
    if not 0 < float(config.get("test_size", 0.2)) < 1:
        raise ValueError("test_size must be between 0 and 1")
    return config


def train(config_path: str | Path = DEFAULT_CONFIG, output_path: str | Path | None = None) -> dict:
    config = load_config(config_path)
    dataset = load_breast_cancer()
    X_train, X_test, y_train, y_test = train_test_split(
        dataset.data, dataset.target,
        test_size=float(config.get("test_size", 0.2)),
        random_state=int(config.get("random_state", 42)),
        stratify=dataset.target,
    )
    model = RandomForestClassifier(
        n_estimators=int(config.get("n_estimators", 200)),
        max_depth=config.get("max_depth"),
        min_samples_split=int(config.get("min_samples_split", 2)),
        min_samples_leaf=int(config.get("min_samples_leaf", 1)),
        random_state=int(config.get("random_state", 42)),
        n_jobs=-1,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "f1": float(f1_score(y_test, predictions, pos_label=0, zero_division=0)),
        "precision": float(precision_score(y_test, predictions, pos_label=0, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, pos_label=0, zero_division=0)),
        "dataset": "sklearn.datasets.load_breast_cancer",
        "positive_class": "malignant (target=0); F1, precision and recall use pos_label=0",
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "feature_count": int(dataset.data.shape[1]),
        "config": config,
    }
    # Persist feature names and target labels alongside the fitted estimator.
    artifact = {"model": model, "feature_names": dataset.feature_names.tolist(), "target_names": dataset.target_names.tolist()}
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(artifact, output)
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output", default=str(ROOT / "artifacts" / "candidate.joblib"))
    parser.add_argument("--metrics", default=str(ROOT / "artifacts" / "candidate_metrics.json"))
    args = parser.parse_args()
    result = train(args.config, args.output)
    Path(args.metrics).parent.mkdir(parents=True, exist_ok=True)
    Path(args.metrics).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
