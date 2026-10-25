pipeline {
    agent any
    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '15'))
    }
    environment {
        PYTHONUNBUFFERED = '1'
        STATE_DIR = "${env.JENKINS_HOME}/ml-devops-state"
        APP_CONTAINER = 'breast-cancer-api'
        APP_IMAGE = 'breast-cancer-api'
        APP_PORT = '8000'
    }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Prepare Python') {
            steps {
                sh '''
                    python3 --version
                    python3 -m venv .venv
                    .venv/bin/python -m pip install --upgrade pip
                    .venv/bin/pip install -r requirements.txt
                    mkdir -p artifacts "$STATE_DIR"
                '''
            }
        }
        stage('Unit Tests') {
            steps { sh '.venv/bin/python -m pytest -q' }
        }
        stage('Train Candidate') {
            steps {
                sh '''
                    .venv/bin/python src/train.py \
                      --output artifacts/candidate.joblib \
                      --metrics artifacts/candidate_metrics.json
                '''
                archiveArtifacts artifacts: 'artifacts/candidate_metrics.json', fingerprint: true
            }
        }
        stage('Evaluate Against Incumbent') {
            steps {
                sh '''
                    .venv/bin/python src/evaluate.py \
                      --candidate artifacts/candidate.joblib \
                      --incumbent "$STATE_DIR/incumbent.joblib" \
                      --candidate-metrics artifacts/candidate_metrics.json \
                      --decision artifacts/decision.json
                    cat artifacts/decision.json
                '''
                script {
                    env.DEPLOY_DECISION = sh(script: ".venv/bin/python -c \"import json; print(json.load(open('artifacts/decision.json'))['decision'])\"", returnStdout: true).trim()
                }
                archiveArtifacts artifacts: 'artifacts/decision.json', fingerprint: true
            }
        }
        stage('Build Candidate Image') {
            when { expression { env.DEPLOY_DECISION == 'deploy' } }
            steps {
                sh '''docker build \
                  --build-arg MODEL_PATH=artifacts/candidate.joblib \
                  --build-arg METRICS_PATH=artifacts/candidate_metrics.json \
                  --build-arg DECISION_PATH=artifacts/decision.json \
                  -t "$APP_IMAGE:candidate-$BUILD_NUMBER" .'''
            }
        }
        stage('Deploy With Health Check') {
            when { expression { env.DEPLOY_DECISION == 'deploy' } }
            steps {
                sh '''
                    chmod +x scripts/deploy.sh
                    scripts/deploy.sh "$APP_IMAGE:candidate-$BUILD_NUMBER" "$APP_CONTAINER" "$APP_PORT"
                    docker tag "$APP_IMAGE:candidate-$BUILD_NUMBER" "$APP_IMAGE:latest"
                    # Only promote the incumbent after deployment and health check succeed.
                    cp artifacts/candidate.joblib "$STATE_DIR/incumbent.joblib.tmp"
                    mv "$STATE_DIR/incumbent.joblib.tmp" "$STATE_DIR/incumbent.joblib"
                    cp artifacts/candidate_metrics.json "$STATE_DIR/incumbent_metrics.json.tmp"
                    mv "$STATE_DIR/incumbent_metrics.json.tmp" "$STATE_DIR/incumbent_metrics.json"
                    cp artifacts/decision.json "$STATE_DIR/last-decision.json"
                '''
            }
        }
        stage('Keep Existing Deployment') {
            when { expression { env.DEPLOY_DECISION == 'reject' } }
            steps {
                echo 'Candidate did not beat the incumbent. Existing container and incumbent artifact remain unchanged.'
                sh 'cp artifacts/decision.json "$STATE_DIR/last-decision.json"'
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'artifacts/*.json', allowEmptyArchive: true, fingerprint: true
        }
    }
}
