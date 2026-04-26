# ACEest Fitness & Gym — DevOps CI/CD Pipeline
## Assignment 2 Report

**Course:** Introduction to DevOps (CSIZG514/SEZG514) — S1-25  
**Application:** ACEest Fitness & Gym (Flask Web Application)  
**Repository:** https://github.com/phanibitsbyte/aceest-fitness  
**Docker Hub:** https://hub.docker.com/r/phanibitsbyte/aceest-fitness  

---

## 1. CI/CD Architecture Overview

```
Developer Push
      │
      ▼
 GitHub (main / develop branch)
      │  Webhook / SCM Poll
      ▼
 ┌─────────────────────────────────────────────────────────┐
 │                    Jenkins Pipeline                     │
 │                                                         │
 │  Checkout → Install Deps → Lint (flake8 + bandit) →    │
 │  Pytest + Coverage → SonarQube Analysis →              │
 │  Quality Gate → Docker Build → Docker Hub Push →       │
 │  Deploy to Minikube (Rolling Update)                    │
 └─────────────────────────────────────────────────────────┘
      │                          │
      ▼                          ▼
 Docker Hub                  Minikube
 phanibitsbyte/              ┌──────────────────────┐
 aceest-fitness               │ aceest-fitness ns    │
  :v1.0 → :v3.2.4            │ Rolling Update (3x)  │
  :latest                    │ Blue-Green           │
                              │ Canary (9+1 pods)    │
                              │ A/B Testing          │
                              │ Shadow               │
                              └──────────────────────┘
```

### Infrastructure Stack

| Component | Tool | Purpose |
|---|---|---|
| Source Control | Git + GitHub | Version control, branch strategy |
| CI Server | Jenkins (Docker) | Automated build & test |
| Code Quality | SonarQube Community | Static analysis, quality gates |
| Testing | Pytest + pytest-cov | Unit tests, coverage reports |
| Security Scan | Bandit + pip-audit | SAST and dependency vulnerabilities |
| Containerisation | Docker (multi-stage) | Immutable, reproducible builds |
| Registry | Docker Hub | Versioned image storage |
| Orchestration | Kubernetes / Minikube | Deployment, scaling, rollback |
| Ingress | NGINX Ingress Controller | Routing, A/B cookie-based split |

---

## 2. Application Versions

The application evolved through 10 incremental versions, each adding capabilities:

| Version | Key Features |
|---|---|
| v1.0 | Static program display (Fat Loss, Muscle Gain, Beginner) |
| v1.1 | Calorie estimation, client profile form |
| v2.1.2 | SQLite persistence, client save/load |
| v2.2.1 | Height/target weight, progress tracking, matplotlib charts |
| v2.2.4 | Workout session logging, exercise tracking |
| v3.0.1 | Role-based login (Admin/Trainer), membership expiry |
| v3.1.2 | PDF reports, AI program generator, chart API |
| v3.2.4 | Full production Flask app (current `main`) |

All versions are available as Docker images on Docker Hub (`phanibitsbyte/aceest-fitness:vX.Y.Z`).

---

## 3. Jenkins Pipeline Stages

### Stage 1 — Checkout
`checkout scm` pulls the latest code from the configured GitHub branch.

### Stage 2 — Install Dependencies
Installs both production (`requirements.txt`) and development (`requirements-dev.txt`) dependencies via pip.

### Stage 3 — Lint
- **flake8**: PEP-8 style enforcement (max line length 120)
- **Bandit**: SAST scan for common Python security issues
- **pip-audit**: Checks for known CVEs in dependency versions

### Stage 4 — Test + Coverage
Pytest executes the full test suite (`tests/test_app.py`). Results:
- JUnit XML → Jenkins Test Results tab
- Coverage XML → Jenkins Coverage Report (Cobertura format)
- Assignment 1 achieved **97.92% line coverage**

### Stage 5 — SonarQube Analysis
The `sonar-scanner` CLI submits source code and coverage data to the SonarQube server running at `http://sonarqube:9000`. Configured via `sonar-project.properties`.

### Stage 6 — Quality Gate
`waitForQualityGate` blocks the pipeline until SonarQube returns a PASS/FAIL verdict. A FAIL aborts the pipeline — preventing bad code from reaching Docker Hub or Kubernetes.

### Stage 7 — Docker Build
Multi-stage Dockerfile with `--target production` ensures only runtime dependencies are included. The image is tagged with both the Jenkins build number and semantic version (`v3.2.4`).

### Stage 8 — Docker Hub Push
Uses the `DOCKERHUB_CREDENTIALS` Jenkins credential (stored as Username/Password). Pushes three tags: `:<build-number>`, `:v3.2.4`, and `:latest`.

### Stage 9 — Deploy to Minikube
Applies Kubernetes manifests and updates the Rolling Update deployment image. On failure, `kubectl rollout undo` is automatically triggered in the `post { failure }` block.

---

## 4. Deployment Strategies

### 4.1 Rolling Update (`k8s/rolling-update/`)
**How it works:** Kubernetes replaces pods one at a time. With `maxSurge: 1` and `maxUnavailable: 0`, at no point are there fewer than 3 healthy pods serving traffic.

**Rollback:** `kubectl rollout undo deployment/aceest-rolling -n aceest-fitness`

```
Before: [v3.1.2] [v3.1.2] [v3.1.2]
Step 1: [v3.1.2] [v3.1.2] [v3.2.4]  ← new pod passes readiness probe
Step 2: [v3.1.2] [v3.2.4] [v3.2.4]
Step 3: [v3.2.4] [v3.2.4] [v3.2.4]  ← complete
```

### 4.2 Blue-Green Deployment (`k8s/blue-green/`)
**How it works:** Two identical environments run in parallel. The Service selector points to `slot: blue` (current stable). After verifying green, traffic is switched instantly by patching the selector.

**Cutover:** `bash scripts/switch-to-green.sh`  
**Rollback:** `bash scripts/rollback-to-blue.sh` (instant — no new pods needed)

```
Traffic → Service (selector: slot=blue) → [Blue pods: v3.2.4]
                                           [Green pods: v3.1.2] ← idle

After switch:
Traffic → Service (selector: slot=green) → [Green pods: v3.1.2]
                                            [Blue pods: v3.2.4] ← idle (kept for fast rollback)
```

### 4.3 Canary Release (`k8s/canary/`)
**How it works:** 9 stable pods (v3.1.2) + 1 canary pod (v3.2.4). A shared Service with selector `app: aceest-fitness` routes requests to all 10 pods proportionally — giving ~10% of real traffic to the canary.

**Promote:** Scale canary to 10, scale stable to 0.  
**Abort:** `kubectl delete deployment aceest-canary -n aceest-fitness`

### 4.4 A/B Testing (`k8s/ab-testing/`)
**How it works:** Two separate deployments with different `variant` labels (a=v3.2.4, b=v3.1.2). NGINX Ingress uses the `canary-by-cookie: variant` annotation — users with cookie `variant=b` always reach Variant B; others are split 50/50 by weight.

**Use case:** Measuring user engagement differences between UI/UX variants.

### 4.5 Shadow Deployment (`k8s/shadow/`)
**How it works:** The production deployment handles all real user traffic. A shadow deployment receives a mirrored copy of every request via NGINX `mirror` directive. The shadow's responses are silently dropped — users never see them.

**Use case:** Testing new version behaviour against production traffic patterns with zero user risk.

---

## 5. SonarQube Code Quality

SonarQube is integrated as a Docker Compose service (`sonarqube:10-community` backed by PostgreSQL).

**Configuration:** `sonar-project.properties` defines:
- Project key: `aceest-fitness`
- Source: `app.py`
- Test path: `tests/`
- Coverage report: `coverage.xml` (generated by pytest-cov)
- Quality Gate: enabled (`sonar.qualitygate.wait=true`)

**Metrics tracked:** Bugs, Vulnerabilities, Code Smells, Security Hotspots, Coverage %, Duplications.

---

## 6. Challenges and Mitigations

| Challenge | Mitigation |
|---|---|
| Jenkins JUnit/Coverage plugin incompatibility | Replaced `cobertura()` with `recordCoverage()` (Coverage Plugin, not Cobertura Plugin) |
| Docker-in-Docker on Jenkins | Used Docker-outside-of-Docker by mounting `/var/run/docker.sock` into the Jenkins container |
| SonarQube requires `vm.max_map_count` on Linux | Documented `sysctl` command in docker-compose.yml comments; set automatically on Docker Desktop |
| SQLite is not multi-replica safe | PVC with `ReadWriteOnce` used; for multi-replica scenarios, PostgreSQL migration path is available |
| Minikube PVC with `standard` StorageClass | Minikube's built-in `standard` dynamic provisioner handles PVC automatically |
| A/B routing without service mesh | Used NGINX Ingress canary annotations (cookie-based) — no Istio/Linkerd required |

---

## 7. Rollback Procedure

### Automatic (via Jenkins)
If any pipeline stage fails, the `post { failure }` block runs:
```groovy
kubectl rollout undo deployment/aceest-rolling -n aceest-fitness
```

### Manual Rollback Options

```bash
# Rolling Update — revert to previous image
kubectl rollout undo deployment/aceest-rolling -n aceest-fitness

# Blue-Green — instant switch back to blue
bash scripts/rollback-to-blue.sh

# Canary — remove canary deployment (stable continues serving 100%)
kubectl delete deployment aceest-canary -n aceest-fitness

# Deploy specific version tag
kubectl set image deployment/aceest-rolling \
  aceest-fitness=phanibitsbyte/aceest-fitness:v3.1.2 \
  -n aceest-fitness
```

---

## 8. Key Automation Outcomes

- **Zero-touch deployment:** A `git push` to `develop` triggers the full pipeline automatically via Jenkins SCM polling.
- **Quality enforcement:** SonarQube Quality Gate blocks promotion of code with critical bugs or coverage regression.
- **Immutable artefacts:** Every build produces a uniquely tagged Docker image — old versions remain deployable at any time.
- **Multi-strategy readiness:** All 5 Kubernetes deployment strategies are pre-configured and deployable with a single `kubectl apply`.
- **Automated rollback:** Deployment failures trigger automatic rollback without manual intervention.

---

## 9. Repository Structure

```
aceest-fitness/
├── app.py                          # Main Flask application (v3.2.4)
├── Dockerfile                      # Multi-stage: test + production
├── Dockerfile.jenkins              # Jenkins with Docker + Python tools
├── docker-compose.yml              # Flask + Jenkins + SonarQube
├── Jenkinsfile                     # Full 9-stage CI/CD pipeline
├── sonar-project.properties        # SonarQube configuration
├── requirements.txt                # Production dependencies
├── requirements-dev.txt            # Dev/test dependencies
├── tests/
│   └── test_app.py                 # Pytest test suite (97.92% coverage)
├── versions/
│   ├── v1.0/app.py  →  v3.1.2/app.py   # Incremental version history
├── k8s/
│   ├── namespace.yaml, configmap.yaml, pvc.yaml, service.yaml
│   ├── hpa.yaml, ingress.yaml
│   ├── rolling-update/deployment.yaml
│   ├── blue-green/{blue,green}-deployment.yaml + service.yaml
│   ├── canary/{stable,canary}-deployment.yaml + service.yaml
│   ├── ab-testing/{variant-a,variant-b}.yaml + ingress.yaml
│   └── shadow/{production,shadow}-deployment.yaml + mirror-service.yaml
├── scripts/
│   ├── rollback.sh
│   ├── switch-to-green.sh
│   ├── rollback-to-blue.sh
│   └── build-push-all-versions.sh
└── docs/
    └── Assignment2-Report.md       # This document
```
