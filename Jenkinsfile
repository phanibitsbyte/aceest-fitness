// ============================================================
// ACEest Fitness & Gym – Jenkinsfile (Assignment 2)
// Full CI/CD Pipeline:
//   Checkout → Install → Lint → Test → SonarQube Analysis →
//   Quality Gate → Docker Build → Docker Hub Push → Deploy to Minikube
//
// Jenkins Credentials required (Manage Jenkins → Credentials):
//   DOCKERHUB_CREDENTIALS  : Username/Password  (Docker Hub login)
//   SONARQUBE_TOKEN        : Secret Text        (SonarQube user token)
//   KUBECONFIG_FILE        : Secret File        (kubectl config for Minikube)
//
// Jenkins Plugin requirements:
//   - JUnit Plugin
//   - Coverage Plugin
//   - SonarQube Scanner Plugin (Manage Jenkins → Configure System → SonarQube servers)
//   - Docker Pipeline Plugin
//   - Kubernetes CLI Plugin
// ============================================================

pipeline {
    agent any

    environment {
        APP_NAME      = 'aceest-fitness'
        DOCKERHUB_USER = 'phanibitsbyte'
        IMAGE_REPO    = "${DOCKERHUB_USER}/${APP_NAME}"
        IMAGE_TAG     = "${env.BUILD_NUMBER}"
        PYTHON        = 'python3'
        DB_NAME       = 'test_aceest.db'
        K8S_NAMESPACE = 'aceest-fitness'
    }

    stages {

        // ── Stage 1: Checkout ────────────────────────────────
        stage('Checkout') {
            steps {
                echo "==> Checking out source code from GitHub..."
                checkout scm
            }
        }

        // ── Stage 2: Install Dependencies ────────────────────
        stage('Install Dependencies') {
            steps {
                echo "==> Installing Python dependencies..."
                sh "${PYTHON} -m pip install --upgrade pip"
                sh "${PYTHON} -m pip install -r requirements-dev.txt"
            }
        }

        // ── Stage 3: Lint + Security Scan ────────────────────
        stage('Lint') {
            steps {
                echo "==> Running flake8 linter..."
                sh "${PYTHON} -m flake8 app.py tests/ --max-line-length=120 --statistics"
                echo "==> Running Bandit security scan (SAST)..."
                sh "${PYTHON} -m bandit -r app.py -ll -f txt || true"
                echo "==> Checking dependencies for known vulnerabilities..."
                sh "${PYTHON} -m pip_audit -r requirements.txt || true"
            }
        }

        // ── Stage 4: Test + Coverage ─────────────────────────
        stage('Test') {
            steps {
                echo "==> Running Pytest suite with coverage..."
                sh """
                    ${PYTHON} -m pytest tests/ -v --tb=short \
                        --cov=app \
                        --cov-report=xml:coverage.xml \
                        --cov-report=term-missing \
                        --junitxml=test-results.xml
                """
            }
            post {
                always {
                    junit testResults: 'test-results.xml', allowEmptyResults: true
                    recordCoverage(
                        tools: [[parser: 'COBERTURA', pattern: 'coverage.xml']],
                        id: 'coverage',
                        name: 'ACEest Coverage Report',
                        failOnError: false,
                        sourceCodeRetention: 'EVERY_BUILD'
                    )
                    archiveArtifacts artifacts: 'test-results.xml, coverage.xml', allowEmptyArchive: true
                }
            }
        }

        // ── Stage 5: SonarQube Analysis ──────────────────────
        stage('SonarQube Analysis') {
            steps {
                echo "==> Running SonarQube static analysis..."
                withSonarQubeEnv('SonarQube') {
                    sh """
                        sonar-scanner \
                          -Dsonar.projectKey=aceest-fitness \
                          -Dsonar.projectName='ACEest Fitness & Gym' \
                          -Dsonar.projectVersion=3.2.4 \
                          -Dsonar.sources=app.py \
                          -Dsonar.tests=tests \
                          -Dsonar.python.coverage.reportPaths=coverage.xml \
                          -Dsonar.host.url=${SONAR_HOST_URL} \
                          -Dsonar.login=${SONAR_AUTH_TOKEN}
                    """
                }
            }
        }

        // ── Stage 6: Quality Gate ─────────────────────────────
        stage('Quality Gate') {
            steps {
                echo "==> Waiting for SonarQube Quality Gate result..."
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        // ── Stage 7: Docker Build ─────────────────────────────
        stage('Docker Build') {
            steps {
                echo "==> Building Docker image: ${IMAGE_REPO}:${IMAGE_TAG}"
                sh "docker build --target production -t ${IMAGE_REPO}:${IMAGE_TAG} ."
                sh "docker tag ${IMAGE_REPO}:${IMAGE_TAG} ${IMAGE_REPO}:latest"
                sh "docker tag ${IMAGE_REPO}:${IMAGE_TAG} ${IMAGE_REPO}:v3.2.4"
            }
        }

        // ── Stage 8: Docker Hub Push ──────────────────────────
        stage('Docker Hub Push') {
            steps {
                echo "==> Pushing image to Docker Hub..."
                withCredentials([usernamePassword(
                    credentialsId: 'DOCKERHUB_CREDENTIALS',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh "echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin"
                    sh "docker push ${IMAGE_REPO}:${IMAGE_TAG}"
                    sh "docker push ${IMAGE_REPO}:latest"
                    sh "docker push ${IMAGE_REPO}:v3.2.4"
                    sh "docker logout"
                }
            }
        }

        // ── Stage 9: Deploy to Minikube (Rolling Update) ─────
        stage('Deploy to Minikube') {
            steps {
                echo "==> Deploying to Minikube via Rolling Update..."
                withCredentials([file(credentialsId: 'KUBECONFIG_FILE', variable: 'KUBECONFIG')]) {
                    sh "kubectl apply -f k8s/namespace.yaml"
                    sh "kubectl apply -f k8s/configmap.yaml"
                    sh "kubectl apply -f k8s/pvc.yaml"
                    sh "kubectl apply -f k8s/service.yaml"
                    sh "kubectl apply -f k8s/rolling-update/deployment.yaml -n ${K8S_NAMESPACE}"
                    sh """
                        kubectl set image deployment/aceest-rolling \
                          aceest-fitness=${IMAGE_REPO}:${IMAGE_TAG} \
                          -n ${K8S_NAMESPACE}
                    """
                    sh "kubectl rollout status deployment/aceest-rolling -n ${K8S_NAMESPACE} --timeout=120s"
                    sh "kubectl get pods -n ${K8S_NAMESPACE}"
                }
            }
        }

    }

    post {
        success {
            echo "✅ Pipeline SUCCESSFUL — ${IMAGE_REPO}:${IMAGE_TAG} deployed via Rolling Update."
        }
        failure {
            echo "❌ Pipeline FAILED — triggering rollback..."
            withCredentials([file(credentialsId: 'KUBECONFIG_FILE', variable: 'KUBECONFIG')]) {
                sh "kubectl rollout undo deployment/aceest-rolling -n ${K8S_NAMESPACE} || true"
            }
        }
        always {
            echo "Pipeline finished at ${new Date()}."
            sh "docker rmi ${IMAGE_REPO}:${IMAGE_TAG} || true"
        }
    }
}
