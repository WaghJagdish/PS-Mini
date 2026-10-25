import json
from pathlib import Path
from src.train import train


def test_train_creates_artifact_and_metrics(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "candidate.joblib"
    metrics = train(root / "config/model.json", output)
    assert output.exists()
    assert 0 <= metrics["accuracy"] <= 1
    assert 0 <= metrics["f1"] <= 1
    assert metrics["feature_count"] == 30
