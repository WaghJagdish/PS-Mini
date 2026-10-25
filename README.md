# ModelOps: Automated ML Retraining & Conditional Docker Deployment.

**Professional Skills Development / DevOps mini-project** using Git, GitHub, Jenkins, Docker, scikit-learn, FastAPI, React/Vite and pytest.

> **Educational demonstration only.** The Breast Cancer Wisconsin dataset and resulting classifier are not intended for clinical decisions, screening, diagnosis or treatment. The UI's predictions are software-demo outputs only.

## Features 

- React dashboard with Accuracy, F1, Precision and Recall from the packaged model metrics.
- 30-feature prediction form with a sample-row loader.
- Dashboard view of the model decision artifact (candidate vs incumbent).
- FastAPI API and static frontend served from the same Docker container at port 8000.
- Jenkins runs tests and retrains a Random Forest on each GitHub push.
- Candidate and incumbent are evaluated on the same deterministic stratified holdout split.
- F1 is the primary selection metric; accuracy breaks ties. Exact ties retain the incumbent.
- Candidate image is health-checked before deployment. Deployment failures attempt to restore the previous container.
- Only after successful deployment does Jenkins promote the candidate model and metrics to persistent state under `$JENKINS_HOME/ml-devops-state`.

## Architecture(system design)

```text
GitHub push / webhook
        |
        v
Jenkins: checkout -> install -> pytest -> train candidate
        |
        v
Evaluate candidate vs persistent incumbent on the same test split
        |
        +---- Candidate wins ----> Build Docker image (React + FastAPI + model)
        |                                  |
        |                                  v
        |                         health check -> deploy -> promote incumbent
        |
        +---- Candidate loses ---> keep running container and incumbent unchanged
```

## Repository layout

```text
ml-devops-pipeline/
├── app/main.py             # FastAPI prediction API + dashboard endpoints + static UI
├── frontend/               # React + Vite dashboard
│   ├── src/main.jsx
│   ├── src/styles.css
│   ├── package.json
│   └── vite.config.js
├── src/train.py            # Candidate training
├── src/evaluate.py         # Candidate vs incumbent comparison
├── tests/                  # Unit/API tests
├── config/model.json       # Hyperparameters and metric policy
├── scripts/deploy.sh       # Health checks and rollback
├── Dockerfile              # Multi-stage frontend build + Python runtime
├── Jenkinsfile
├── requirements.txt
└── README.md
```

## 1. Install prerequisites on macOS

Install Homebrew if needed from https://brew.sh/, then:

```bash
brew update
brew install git python@3.11 jenkins-lts
```

Install Docker Desktop from https://www.docker.com/products/docker-desktop/, open it and wait until the Docker engine is running. Start Jenkins:

```bash
brew services start jenkins-lts
```

Open http://localhost:8080. The initial unlock password is often at:

```bash
cat ~/.jenkins/secrets/initialAdminPassword
```

If the file is missing, check Jenkins logs and the actual `JENKINS_HOME` in **Manage Jenkins → System Information**. Install suggested plugins, including Pipeline, Git and GitHub. Jenkins must be able to execute `python3`, `docker` and `curl`. The React build runs inside the Docker multi-stage build, so Node/npm do not need to be installed directly on the Jenkins host. Docker Desktop must be running for the Jenkins service account. On Apple Silicon, Homebrew is commonly under `/opt/homebrew/bin`; on Intel, commonly `/usr/local/bin`. Configure Jenkins' PATH if needed.

## 2. Create the GitHub repository

Create an **empty** GitHub repository named `ml-devops-pipeline` (don't add a README online if using these commands). In Terminal, move into the extracted project folder, then:

```bash
git init
git add .
git commit -m "Initial ML DevOps dashboard and pipeline"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ml-devops-pipeline.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username. GitHub authentication may require a browser-based sign-in or a personal access token; don't put tokens in source code.

## 3. Run tests and train locally first

From the project root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pytest -q
python src/train.py
python src/evaluate.py \
  --candidate artifacts/candidate.joblib \
  --incumbent artifacts/first-run-no-incumbent.joblib \
  --candidate-metrics artifacts/candidate_metrics.json \
  --decision artifacts/decision.json
```

The missing incumbent path on the first run is intentional: the evaluator will mark the first candidate eligible for deployment. The dataset is bundled in scikit-learn; no separate CSV download is needed.

## 4. Build and run the API + React dashboard in Docker

Docker Desktop must be running. The previous step must have generated the model, metrics and decision artifacts.

```bash
docker build \
  --build-arg MODEL_PATH=artifacts/candidate.joblib \
  --build-arg METRICS_PATH=artifacts/candidate_metrics.json \
  --build-arg DECISION_PATH=artifacts/decision.json \
  -t breast-cancer-api:local .

docker run -d --name breast-cancer-api-local -p 8000:8000 breast-cancer-api:local
```

Open the frontend at **http://localhost:8000/**. The interactive API docs are at http://localhost:8000/docs. Verify endpoints:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/model-info
curl http://localhost:8000/dashboard
curl http://localhost:8000/sample-input
```

After testing, remove the local container:

```bash
docker rm -f breast-cancer-api-local
```

The dashboard displays the metrics and decision JSON baked into the currently running image. For live Jenkins build history, open the Jenkins job's **Build History / Console Output**. The frontend deliberately does not expose Jenkins credentials to the browser.

## 5. Configure the Jenkins pipeline

1. Open Jenkins at http://localhost:8080.
2. Select **New Item**, name it `ml-devops-pipeline`, and choose **Pipeline**.
3. Under **Build Triggers**, enable **GitHub hook trigger for GITScm polling** if available.
4. Under **Pipeline**, select **Pipeline script from SCM**.
5. Select **Git**, enter the repository URL, set branch to `*/main`, and script path to `Jenkinsfile`.
6. Save and click **Build Now** for the first run.
7. Confirm the console shows checkout, dependency installation, tests, training, comparison, Docker build and health-checked deployment.

The Jenkins agent needs Docker access and Node/npm for the multi-stage Docker build. Check with a Jenkins shell step if builds fail:

```bash
which python3; python3 --version
which docker; docker version
which curl
```

If the Homebrew Jenkins service has a different PATH, configure it in Jenkins global environment variables or start the service with the correct PATH. Never fix a Docker permission issue by exposing an unauthenticated Docker TCP API.

## 6. Trigger on every GitHub push

A GitHub webhook needs a public HTTPS endpoint; GitHub cannot reach `localhost:8080` directly. For a temporary classroom demo, a permitted HTTPS tunnel such as ngrok can expose the Jenkins webhook endpoint:

1. Start a tunnel to Jenkins port 8080, e.g. `ngrok http 8080`.
2. In GitHub → repository **Settings → Webhooks → Add webhook**, set Payload URL to `https://YOUR-TUNNEL-DOMAIN/github-webhook/`.
3. Select content type `application/json` and **Just the push event**.
4. Ensure the Jenkins job has **GitHub hook trigger for GITScm polling** enabled.
5. Push a small change and inspect GitHub's **Recent deliveries** and Jenkins Build History.

Protect Jenkins with authentication; do not expose an unsecured Jenkins instance publicly. If a tunnel is not allowed, configure **Poll SCM** in the job (e.g. `* * * * *`) as an alternative. Polling detects pushes periodically rather than instantly.

## 7. Demonstrate conditional model promotion

- **First successful run:** no incumbent exists, so the first candidate is eligible for deployment.
- **Candidate improves F1:** build image, health-check and deploy; then promote model and metrics into persistent incumbent storage.
- **Candidate loses or ties:** reject it; current container and incumbent stay unchanged.
- **Deployment health check fails:** deployment script attempts to roll back to the old image.
- **Tests fail:** pipeline stops before deployment.

To trigger retraining, change a model setting in `config/model.json` (for example `n_estimators`) or edit a Python training file, then commit and push. Changing a hyperparameter does **not** guarantee the metric improves; the measured evaluation result determines the outcome. Inspect archived `candidate_metrics.json` and `decision.json` in Jenkins for evidence.

Persistent state lives at `$JENKINS_HOME/ml-devops-state/` on the Jenkins host. Do not delete that folder between builds if you want incumbent comparisons to persist.

## 8. Demo checklist

- [ ] Show GitHub repository and `Jenkinsfile`.
- [ ] Show successful first pipeline run.
- [ ] Open the dashboard and show model metrics.
- [ ] Use **Load sample** in Prediction Lab and run a prediction.
- [ ] Change a hyperparameter and push to GitHub.
- [ ] Show Jenkins triggering automatically.
- [ ] Show candidate vs incumbent metrics and the deploy/reject decision in the build artifacts.
- [ ] Show the running Docker container and `/health` endpoint.
- [ ] Explain persistent incumbent storage and rollback behavior.

## Notes and limitations

- The UI's candidate/incumbent comparison is the decision artifact packaged with the deployed image. A rejected run does not replace the running image, so view Jenkins artifacts/console for the latest rejected decision.
- This project uses a deterministic holdout split to demonstrate CI/CD, not a rigorous clinical model validation process. Repeated model selection against one test split can cause test-set overfitting.
- This is a student project, not a production-ready ML platform. Production systems should add authentication, immutable artifact storage, data/model versioning, drift monitoring, security hardening and stronger deployment orchestration.
