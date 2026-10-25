import joblib
import numpy as np
from fastapi.testclient import TestClient
from sklearn.datasets import load_breast_cancer
from sklearn.dummy import DummyClassifier
import app.main as api


def make_artifact(path):
    data = load_breast_cancer()
    model = DummyClassifier(strategy="most_frequent")
    model.fit(data.data, data.target)
    joblib.dump({"model": model, "feature_names": data.feature_names.tolist(), "target_names": data.target_names.tolist()}, path)


def test_health_and_model_info(tmp_path, monkeypatch):
    model_path = tmp_path / "model.joblib"
    make_artifact(model_path)
    monkeypatch.setattr(api, "MODEL_PATH", model_path)
    with TestClient(api.app) as client:
        assert client.get("/health").json() == {"status": "ok", "model_loaded": True}
        assert client.get("/model-info").json()["feature_count"] == 30


def test_predict_requires_exactly_30_features(tmp_path, monkeypatch):
    model_path = tmp_path / "model.joblib"
    make_artifact(model_path)
    monkeypatch.setattr(api, "MODEL_PATH", model_path)
    with TestClient(api.app) as client:
        response = client.post("/predict", json={"features": [1.0, 2.0]})
        assert response.status_code == 422


def test_predict_returns_prediction(tmp_path, monkeypatch):
    model_path = tmp_path / "model.joblib"
    make_artifact(model_path)
    monkeypatch.setattr(api, "MODEL_PATH", model_path)
    with TestClient(api.app) as client:
        data = load_breast_cancer()
        response = client.post("/predict", json={"features": data.data[0].tolist()})
        assert response.status_code == 200
        assert response.json()["class_name"] in {"malignant", "benign"}


def test_sample_input_has_30_named_features(tmp_path, monkeypatch):
    model_path = tmp_path / "model.joblib"
    make_artifact(model_path)
    monkeypatch.setattr(api, "MODEL_PATH", model_path)
    with TestClient(api.app) as client:
        response = client.get("/sample-input")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["features"]) == 30
        assert len(payload["feature_names"]) == 30


def test_dashboard_returns_metrics_and_decision(tmp_path, monkeypatch):
    model_path = tmp_path / "model.joblib"
    make_artifact(model_path)
    metrics_path = tmp_path / "metrics.json"
    decision_path = tmp_path / "decision.json"
    metrics_path.write_text('{"accuracy": 0.95, "f1": 0.94, "precision": 0.93, "recall": 0.92}')
    decision_path.write_text('{"decision": "deploy", "reason": "First model"}')
    monkeypatch.setattr(api, "MODEL_PATH", model_path)
    monkeypatch.setattr(api, "METRICS_PATH", metrics_path)
    monkeypatch.setattr(api, "DECISION_PATH", decision_path)
    with TestClient(api.app) as client:
        response = client.get("/dashboard")
        assert response.status_code == 200
        payload = response.json()
        assert payload["metrics"]["f1"] == 0.94
        assert payload["decision"]["decision"] == "deploy"
