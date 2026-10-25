# Build the React dashboard.
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Runtime image for the FastAPI API + static dashboard.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    MODEL_PATH=/app/models/model.joblib \
    METRICS_PATH=/app/models/metrics.json \
    DECISION_PATH=/app/models/decision.json \
    FRONTEND_PATH=/app/frontend_dist
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
ARG MODEL_PATH=artifacts/candidate.joblib
ARG METRICS_PATH=artifacts/candidate_metrics.json
ARG DECISION_PATH=artifacts/decision.json
COPY ${MODEL_PATH} /app/models/model.joblib
COPY ${METRICS_PATH} /app/models/metrics.json
COPY ${DECISION_PATH} /app/models/decision.json
COPY --from=frontend-build /frontend/dist/ /app/frontend_dist/
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
