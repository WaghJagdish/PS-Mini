"""Prediction API and static React dashboard for the educational ModelOps demo."""
from pathlib import Path
import json
import os
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sklearn.datasets import load_breast_cancer

MODEL_PATH = Path(os.getenv("MODEL_PATH", "/app/models/model.joblib"))
METRICS_PATH = Path(os.getenv("METRICS_PATH", "/app/models/metrics.json"))
DECISION_PATH = Path(os.getenv("DECISION_PATH", "/app/models/decision.json"))
FRONTEND_PATH = Path(os.getenv("FRONTEND_PATH", "/app/frontend_dist"))
app = FastAPI(title="ModelOps Breast Cancer Classifier", version="1.1.0", description="Educational ML DevOps demo; not for clinical use.")
artifact = None


class PredictionRequest(BaseModel):
    features: list[float] = Field(..., min_length=30, max_length=30, description="30 numeric features in scikit-learn Breast Cancer Wisconsin dataset order")


@app.on_event("startup")
def load_model() -> None:
    global artifact
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Model artifact not found at {MODEL_PATH}")
    artifact = joblib.load(MODEL_PATH)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": artifact is not None}


@app.get("/model-info")
def model_info() -> dict:
    if artifact is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"model": type(artifact["model"]).__name__, "feature_count": len(artifact["feature_names"]), "feature_names": artifact["feature_names"], "target_names": artifact["target_names"], "warning": "Educational demo only; not for medical diagnosis."}


@app.get("/sample-input")
def sample_input() -> dict:
    """Return a real example row to make the 30-feature demo form usable."""
    data = load_breast_cancer()
    return {"features": data.data[0].astype(float).tolist(), "feature_names": data.feature_names.tolist(), "note": "Example dataset row for software demonstration only; not a patient record."}


@app.get("/dashboard")
def dashboard() -> dict:
    if artifact is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    metrics = None
    decision = None
    try:
        if METRICS_PATH.exists():
            metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        metrics = None
    try:
        if DECISION_PATH.exists():
            decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        decision = None
    return {
        "model": type(artifact["model"]).__name__,
        "feature_count": len(artifact["feature_names"]),
        "metrics": metrics,
        "decision": decision,
        "status": "ok",
        "note": "Decision and metrics describe the build artifacts packaged into this container. See Jenkins for live build history.",
    }


@app.post("/predict")
def predict(request: PredictionRequest) -> dict:
    if artifact is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    values = np.asarray(request.features, dtype=float).reshape(1, -1)
    if not np.isfinite(values).all():
        raise HTTPException(status_code=422, detail="All features must be finite numbers")
    model = artifact["model"]
    prediction = int(model.predict(values)[0])
    probabilities = model.predict_proba(values)[0].tolist() if hasattr(model, "predict_proba") else None
    return {"prediction": prediction, "class_name": artifact["target_names"][prediction], "probabilities": probabilities, "warning": "Educational demo only; not for medical diagnosis."}


# The React production build is served by FastAPI from the same Docker container.
if FRONTEND_PATH.is_dir() and (FRONTEND_PATH / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_PATH), html=True), name="frontend")
