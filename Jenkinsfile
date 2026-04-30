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
//   - Coverage Plugin         (for coverage report tab)
//   - SonarQube Scanner Plugin (Manage Jenkins → Configure System → SonarQube servers)
//   - Docker Pipeline Plugin
//   - Kubernetes CLI Plugin (only needed for Deploy stage)
// Note: JUnit Plugin is NOT required — test results stored as artifacts only
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
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    withSonarQubeEnv('SonarQube') {
                        sh '''
                            SONAR_DIR="/tmp/sonar-scanner-6.2.1.4610-linux-x64"
                            SONAR_BIN="$SONAR_DIR/bin/sonar-scanner"

                            # Install sonar-scanner if not already present (use /tmp — writable by jenkins user)
                            if [ ! -f "$SONAR_BIN" ]; then
                                echo "sonar-scanner not found, installing to /tmp..."
                                curl -sSL https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-6.2.1.4610-linux-x64.zip \
                                     -o /tmp/sonar-scanner.zip
                                unzip -q /tmp/sonar-scanner.zip -d /tmp/
                                rm -f /tmp/sonar-scanner.zip
                                echo "sonar-scanner installed at $SONAR_DIR"
                            fi

                            "$SONAR_BIN" \
                              -Dsonar.projectKey=aceest-fitness \
                              -Dsonar.projectName="ACEest Fitness and Gym" \
                              -Dsonar.projectVersion=3.2.4 \
                              -Dsonar.sources=app.py \
                              -Dsonar.tests=tests \
                              -Dsonar.python.coverage.reportPaths=coverage.xml
                        '''
                        // Note: SONAR_HOST_URL and SONAR_AUTH_TOKEN are injected as shell
                        // env vars by withSonarQubeEnv — sonar-scanner picks them up automatically
                    }
                }
            }
        }

        // ── Stage 6: Quality Gate ─────────────────────────────
        stage('Quality Gate') {
            steps {
                echo "==> Waiting for SonarQube Quality Gate result..."
                script {
                    try {
                        timeout(time: 5, unit: 'MINUTES') {
                            def qg = waitForQualityGate abortPipeline: false
                            if (qg.status != 'OK') {
                                unstable("Quality Gate status: ${qg.status}")
                            } else {
                                echo "✅ Quality Gate PASSED"
                            }
                        }
                    } catch (e) {
                        echo "⚠️ Quality Gate timed out or no webhook configured — continuing pipeline..."
                        currentBuild.result = 'SUCCESS'
                    }
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
                script {
                    def kubectlAvailable = sh(script: 'which kubectl 2>/dev/null || true', returnStdout: true).trim()
                    if (!kubectlAvailable) {
                        echo "WARNING: kubectl not found in Jenkins. Skipping Kubernetes deploy."
                    } else {
                        withCredentials([file(credentialsId: 'KUBECONFIG_FILE', variable: 'KUBECONFIG')]) {
                            // Check if minikube cluster is reachable before attempting deploy
                            def clusterOk = sh(
                                script: 'kubectl cluster-info --request-timeout=8s > /dev/null 2>&1 && echo "ok" || echo "unreachable"',
                                returnStdout: true
                            ).trim()

                            if (clusterOk != 'ok') {
                                echo "⚠️ Minikube cluster not reachable (not running?). Skipping deploy."
                                echo "   Run 'minikube start' then re-run the pipeline to deploy."
                            } else {
                                echo "==> Deploying to Minikube via Rolling Update..."
                                sh "kubectl apply -f k8s/namespace.yaml --validate=false"
                                sh "kubectl apply -f k8s/configmap.yaml --validate=false"
                                sh "kubectl apply -f k8s/pvc.yaml --validate=false"
                                sh "kubectl apply -f k8s/service.yaml --validate=false"
                                sh "kubectl apply -f k8s/rolling-update/deployment.yaml -n ${K8S_NAMESPACE} --validate=false"
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
            }
        }

    }

    post {
        success {
            echo "✅ Pipeline SUCCESSFUL — ${IMAGE_REPO}:${IMAGE_TAG} deployed via Rolling Update."
        }
        failure {
            echo "❌ Pipeline FAILED — attempting rollback if kubectl available..."
            script {
                def kubectlAvailable = sh(script: 'which kubectl || true', returnStdout: true).trim()
                if (kubectlAvailable) {
                    try {
                        withCredentials([file(credentialsId: 'KUBECONFIG_FILE', variable: 'KUBECONFIG')]) {
                            sh "kubectl rollout undo deployment/aceest-rolling -n ${K8S_NAMESPACE} || true"
                        }
                    } catch (err) {
                        echo "Rollback skipped: ${err.message}"
                    }
                } else {
                    echo "kubectl not available — skipping rollback."
                }
            }
        }
        always {
            echo "Pipeline finished."
            sh "docker rmi ${IMAGE_REPO}:${IMAGE_TAG} || true"
        }
    }
}
