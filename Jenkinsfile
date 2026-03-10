// ============================================================
// ACEest Fitness & Gym – Jenkinsfile
// Declarative Pipeline for the Jenkins BUILD stage.
//
// Setup:
//   1. Install Jenkins (https://www.jenkins.io/doc/book/installing/)
//   2. Create a new Pipeline project.
//   3. Set "Pipeline script from SCM" → Git → your GitHub repo URL.
//   4. Ensure the Jenkins agent has Python 3.11+ and Docker installed.
//
// Recommended Jenkins plugins (for full reporting):
//   - JUnit Plugin      → Test Results tab + trend graph  ✅ already installed
//   - Coverage Plugin   → Coverage Report tab + trend graph (NOT "Cobertura Plugin")
//   Install via: Manage Jenkins → Plugins → Available → search "Coverage"
// ============================================================

pipeline {
    agent any

    environment {
        APP_NAME    = 'aceest-fitness'
        PYTHON      = 'python3'
        IMAGE_TAG   = "${env.BUILD_NUMBER}"
        // Isolate test database from any production DB
        DB_NAME     = 'test_aceest.db'
    }

    stages {

        stage('Checkout') {
            steps {
                echo "==> Checking out source code from GitHub..."
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                echo "==> Installing Python dependencies (dev + prod)..."
                sh "${PYTHON} -m pip install --upgrade pip"
                sh "${PYTHON} -m pip install -r requirements-dev.txt"
            }
        }

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
                    echo "Tests completed. Coverage: see coverage.xml artifact."

                    // Publish JUnit test results (requires JUnit Plugin)
                    junit testResults: 'test-results.xml', allowEmptyResults: true

                    // Publish coverage report (requires Coverage Plugin — NOT Cobertura Plugin)
                    // Install: Manage Jenkins → Plugins → Available → search "Coverage"
                    recordCoverage(
                        tools: [[parser: 'COBERTURA', pattern: 'coverage.xml']],
                        id: 'coverage',
                        name: 'ACEest Coverage Report',
                        failOnError: false,
                        sourceCodeRetention: 'EVERY_BUILD'
                    )

                    // Always archive raw XML so reports are downloadable even without plugins
                    archiveArtifacts artifacts: 'test-results.xml, coverage.xml', allowEmptyArchive: true
                }
            }
        }

        stage('Docker Build') {
            steps {
                echo "==> Building Docker image: ${APP_NAME}:${IMAGE_TAG}"
                sh "docker build -t ${APP_NAME}:${IMAGE_TAG} ."
                sh "docker tag ${APP_NAME}:${IMAGE_TAG} ${APP_NAME}:latest"
            }
        }

    }

    post {
        success {
            echo "✅ BUILD SUCCESSFUL – ACEest image ${APP_NAME}:${IMAGE_TAG} is ready."
        }
        failure {
            echo "❌ BUILD FAILED – Review the stage logs above for details."
        }
        always {
            echo "Pipeline finished at ${new Date()}."
        }
    }
}
