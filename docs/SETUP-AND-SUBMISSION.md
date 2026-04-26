# ACEest Fitness & Gym — Assignment 2: Complete Setup & Submission Guide

> **Repo:** https://github.com/phanibitsbyte/aceest-fitness  
> **Docker Hub:** https://hub.docker.com/r/phanibitsbyte/aceest-fitness  
> **Branch to work on:** `develop` (merge to `main` before submission)

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Step 1 — Clone & Branch](#2-step-1--clone--branch)
3. [Step 2 — Start Jenkins + SonarQube with Docker Compose](#3-step-2--start-jenkins--sonarqube-with-docker-compose)
4. [Step 3 — Configure SonarQube](#4-step-3--configure-sonarqube)
5. [Step 4 — Configure Jenkins](#5-step-4--configure-jenkins)
6. [Step 5 — Run Jenkins Pipeline (Verify Green)](#6-step-5--run-jenkins-pipeline-verify-green)
7. [Step 6 — Push Docker Images to Docker Hub](#7-step-6--push-docker-images-to-docker-hub)
8. [Step 7 — Set Up Minikube](#8-step-7--set-up-minikube)
9. [Step 8 — Deploy All 5 Kubernetes Strategies](#9-step-8--deploy-all-5-kubernetes-strategies)
10. [Step 9 — Configure GitHub Actions Secrets](#10-step-9--configure-github-actions-secrets)
11. [Step 10 — Merge develop → main](#11-step-10--merge-develop--main)
12. [Submission Checklist](#12-submission-checklist)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Prerequisites

Install the following tools before starting:

| Tool | Version | Download |
|---|---|---|
| Docker Desktop | Latest | https://www.docker.com/products/docker-desktop |
| Git | 2.x+ | https://git-scm.com |
| Minikube | Latest | https://minikube.sigs.k8s.io/docs/start |
| kubectl | Latest | https://kubernetes.io/docs/tasks/tools |
| Python | 3.11+ | https://www.python.org/downloads |

**Verify installations:**
```bash
docker --version
docker compose version
minikube version
kubectl version --client
python --version
```

**Docker Hub account:** Ensure you are logged in as `phanibitsbyte`:
```bash
docker login -u phanibitsbyte
# Enter your Docker Hub password or Access Token when prompted
```

---

## 2. Step 1 — Clone & Branch

```bash
# Clone the repo (already done at D:\aceest-fitness)
cd D:\aceest-fitness

# Make sure you are on develop
git checkout develop
git pull origin develop

# Verify the file structure
ls k8s/
ls versions/
ls scripts/
```

You should see:
```
k8s/
  namespace.yaml  configmap.yaml  pvc.yaml  service.yaml
  ingress.yaml    hpa.yaml        secret.yaml
  rolling-update/  blue-green/  canary/  ab-testing/  shadow/
versions/
  v1.0/  v1.1/  v2.1.2/  v2.2.1/  v2.2.4/  v3.0.1/  v3.1.2/
scripts/
  rollback.sh  switch-to-green.sh  rollback-to-blue.sh  build-push-all-versions.sh
docs/
  Assignment2-Report.md
```

---

## 3. Step 2 — Start Jenkins + SonarQube with Docker Compose

### 3.1 Increase virtual memory for SonarQube (Linux / WSL only)

SonarQube requires `vm.max_map_count >= 524288`. On Windows with Docker Desktop this is handled automatically.  
On Linux or WSL2, run once:
```bash
sudo sysctl -w vm.max_map_count=524288
echo "vm.max_map_count=524288" | sudo tee -a /etc/sysctl.conf
```

### 3.2 Start all services

```bash
cd D:\aceest-fitness

# Build images and start all containers in background
docker compose up -d --build

# Monitor startup (wait until all services are healthy)
docker compose ps
docker compose logs -f sonarqube   # wait for "SonarQube is operational"
```

### 3.3 Verify services are running

| Service | URL | Default Credentials |
|---|---|---|
| Flask App | http://localhost:5000 | admin / admin |
| Jenkins | http://localhost:8080 | — (see unlock step below) |
| SonarQube | http://localhost:9000 | admin / admin |

> ⏳ SonarQube takes **2–3 minutes** to fully start. Jenkins takes **1–2 minutes**.

---

## 4. Step 3 — Configure SonarQube

### 4.1 First login

1. Open http://localhost:9000
2. Login: **admin / admin**
3. When prompted to change password, set a new one (e.g. `sonar@aceest123`)

### 4.2 Create the project

1. Click **Projects** → **Create Project** → **Manually**
2. **Project key:** `aceest-fitness`
3. **Display name:** `ACEest Fitness & Gym`
4. Click **Set Up**
5. Choose **Use existing CI** → select **Other (for JS, TS, Go, Python, etc.)**
6. OS: **Linux**
7. You will see a `sonar-scanner` command — **copy the token value** shown (e.g. `sqp_abc123...`)

### 4.3 Generate a User Token (for Jenkins)

1. Click your avatar (top-right) → **My Account** → **Security**
2. Under **Generate Tokens**:
   - Name: `jenkins-token`
   - Type: **User Token**
   - Expires: **No expiration**
3. Click **Generate** → **copy the token** (shown only once)
   > Example: `sqp_6e1234abcdef...`
4. Save this token — you will add it to Jenkins in the next step.

---

## 5. Step 4 — Configure Jenkins

### 5.1 Unlock Jenkins

1. Open http://localhost:8080
2. Get the initial admin password:
   ```bash
   docker exec aceest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
   ```
3. Paste the password into the Jenkins unlock page
4. Choose **Install suggested plugins**
5. Create your admin user when prompted

### 5.2 Install required plugins

Go to **Manage Jenkins** → **Plugins** → **Available plugins**, search and install:

| Plugin | Why needed |
|---|---|
| **SonarQube Scanner** | `withSonarQubeEnv()` in Jenkinsfile |
| **Coverage** | `recordCoverage()` in Jenkinsfile |
| **Docker Pipeline** | `docker.build()` and Docker Hub push |
| **Kubernetes CLI** | `withKubeConfig()` for kubectl commands |

After installing, click **Restart Jenkins when no jobs are running**.

### 5.3 Configure SonarQube server in Jenkins

1. **Manage Jenkins** → **Configure System** → scroll to **SonarQube servers**
2. Check **Enable injection of SonarQube server configuration as build environment variables**
3. Click **Add SonarQube**:
   - **Name:** `SonarQube` ← must match Jenkinsfile exactly
   - **Server URL:** `http://sonarqube:9000` ← uses Docker internal network
4. Under **Server authentication token**, click **Add** → **Jenkins**:
   - Kind: **Secret text**
   - Secret: paste the SonarQube token from Step 3.4
   - ID: `SONARQUBE_TOKEN`
5. Select `SONARQUBE_TOKEN` from the dropdown
6. Click **Save**

### 5.4 Install SonarQube Scanner tool

1. **Manage Jenkins** → **Global Tool Configuration** → **SonarQube Scanner**
2. Click **Add SonarQube Scanner**:
   - Name: `SonarScanner`
   - Check **Install automatically**
   - Version: latest
3. Click **Save**

### 5.5 Add Docker Hub credentials

1. **Manage Jenkins** → **Credentials** → **System** → **Global credentials** → **Add Credentials**
2. Fill in:
   - Kind: **Username with password**
   - Username: `phanibitsbyte`
   - Password: your Docker Hub password **or** a Docker Hub Access Token
     > Create an Access Token at: https://hub.docker.com/settings/security
   - ID: `DOCKERHUB_CREDENTIALS` ← must match Jenkinsfile exactly
3. Click **Save**

### 5.6 Add Kubeconfig credential (for kubectl deploy stage)

1. First, export your Minikube kubeconfig:
   ```bash
   minikube start
   # Copy the kubeconfig file:
   copy %USERPROFILE%\.kube\config D:\aceest-fitness\kubeconfig.txt
   ```
2. **Manage Jenkins** → **Credentials** → **Add Credentials**:
   - Kind: **Secret file**
   - File: upload `kubeconfig.txt`
   - ID: `KUBECONFIG_FILE` ← must match Jenkinsfile exactly
3. Click **Save**
4. **Delete** `kubeconfig.txt` from the repo folder after uploading (it contains sensitive info)

### 5.7 Create the Pipeline job

1. **New Item** → Name: `aceest-fitness-pipeline` → **Pipeline** → **OK**
2. Under **Build Triggers**, check **Poll SCM** and set schedule: `H/5 * * * *`
   > This polls GitHub every 5 minutes and triggers on new commits.
3. Under **Pipeline**:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: `https://github.com/phanibitsbyte/aceest-fitness.git`
   - Branch: `*/develop` (or `*/main` after merge)
   - Script Path: `Jenkinsfile`
4. Click **Save**

---

## 6. Step 5 — Run Jenkins Pipeline (Verify Green)

1. On the pipeline page, click **Build Now**
2. Click the build number → **Console Output** to watch live
3. All 9 stages should go green:
   ```
   ✅ Checkout
   ✅ Install Dependencies
   ✅ Lint
   ✅ Test          (97.92% coverage)
   ✅ SonarQube Analysis
   ✅ Quality Gate
   ✅ Docker Build
   ✅ Docker Hub Push
   ✅ Deploy to Minikube
   ```

> **If the Deploy stage fails** because Minikube is not reachable from Docker:  
> Set the Deploy stage to `when { expression { false } }` temporarily to skip it while testing the first 8 stages.

### 5.1 View test results
- Click the build → **Test Results** tab (JUnit results)
- Click **Coverage Report** tab (97.92% line coverage)

### 5.2 View SonarQube results
- Open http://localhost:9000 → **Projects** → `aceest-fitness`
- Check Bugs, Vulnerabilities, Code Smells, Coverage

---

## 7. Step 6 — Push Docker Images to Docker Hub

This step builds and pushes all 8 versioned images to Docker Hub.

### 7.1 Log in to Docker Hub first

```bash
docker login -u phanibitsbyte
```

### 7.2 Run the build-push script

**On Linux/Mac/WSL:**
```bash
cd D:\aceest-fitness
chmod +x scripts/build-push-all-versions.sh
bash scripts/build-push-all-versions.sh
```

**On Windows PowerShell (manually):**
```powershell
cd D:\aceest-fitness
$REPO = "phanibitsbyte/aceest-fitness"

# Build and push each version
docker build --target production -t "${REPO}:v3.2.4" -t "${REPO}:latest" .
docker push "${REPO}:v3.2.4"
docker push "${REPO}:latest"

# Build and push version directories
foreach ($ver in @("v1.0","v1.1","v2.1.2","v2.2.1","v2.2.4","v3.0.1","v3.1.2")) {
    docker build -t "${REPO}:${ver}" versions/$ver
    docker push "${REPO}:${ver}"
}
```

### 7.3 Verify on Docker Hub

Open: https://hub.docker.com/r/phanibitsbyte/aceest-fitness/tags

You should see all these tags:
- `latest`, `v3.2.4`, `v3.1.2`, `v3.0.1`, `v2.2.4`, `v2.2.1`, `v2.1.2`, `v1.1`, `v1.0`

---

## 8. Step 7 — Set Up Minikube

### 8.1 Start Minikube

```bash
# Start with sufficient resources
minikube start --cpus=4 --memory=4096 --driver=docker

# Verify it is running
minikube status
kubectl get nodes
```

Expected output:
```
minikube
type: Control Plane
host: Running
kubelet: Running
apiserver: Running
kubeconfig: Configured
```

### 8.2 Enable required addons

```bash
minikube addons enable ingress       # NGINX Ingress Controller
minikube addons enable metrics-server # Required for HPA
minikube addons list                  # Verify both are enabled
```

### 8.3 Configure Docker to use Minikube's Docker daemon (optional)

This lets Jenkins build images directly inside Minikube:
```bash
# Linux/Mac
eval $(minikube docker-env)

# Windows PowerShell
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
```

---

## 9. Step 8 — Deploy All 5 Kubernetes Strategies

### 9.1 Create the namespace and base resources

```bash
cd D:\aceest-fitness

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Create the secret with a real key (never commit the real value)
kubectl create secret generic aceest-secret \
  --from-literal=SECRET_KEY="MyStr0ngPr0ductionKey2024!" \
  -n aceest-fitness

# Verify
kubectl get all -n aceest-fitness
```

### 9.2 Strategy 1 — Rolling Update

```bash
kubectl apply -f k8s/rolling-update/deployment.yaml -n aceest-fitness
kubectl rollout status deployment/aceest-rolling -n aceest-fitness

# Watch the rolling update in action (update image to trigger it)
kubectl set image deployment/aceest-rolling \
  aceest-fitness=phanibitsbyte/aceest-fitness:v3.1.2 \
  -n aceest-fitness
kubectl rollout status deployment/aceest-rolling -n aceest-fitness

# Rollback
bash scripts/rollback.sh aceest-rolling aceest-fitness
# OR
kubectl rollout undo deployment/aceest-rolling -n aceest-fitness

# Access via Minikube
minikube service aceest-service -n aceest-fitness --url
```

### 9.3 Strategy 2 — Blue-Green Deployment

```bash
# Deploy both blue and green
kubectl apply -f k8s/blue-green/blue-deployment.yaml -n aceest-fitness
kubectl apply -f k8s/blue-green/green-deployment.yaml -n aceest-fitness
kubectl apply -f k8s/blue-green/service.yaml -n aceest-fitness

# Verify both are running
kubectl get pods -n aceest-fitness -l app=aceest-fitness

# Currently traffic → BLUE (v3.2.4)
# Switch to GREEN (v3.1.2)
bash scripts/switch-to-green.sh

# Verify service now points to green
kubectl describe svc aceest-bluegreen-svc -n aceest-fitness | grep Selector

# Rollback to BLUE
bash scripts/rollback-to-blue.sh
```

### 9.4 Strategy 3 — Canary Release

```bash
# Deploy stable (9 replicas) + canary (1 replica)
kubectl apply -f k8s/canary/stable-deployment.yaml -n aceest-fitness
kubectl apply -f k8s/canary/canary-deployment.yaml -n aceest-fitness
kubectl apply -f k8s/canary/service.yaml -n aceest-fitness

# Verify pod distribution (should see 9 stable + 1 canary)
kubectl get pods -n aceest-fitness -l app=aceest-fitness --show-labels

# Promote canary to full rollout (after validation)
kubectl scale deployment aceest-canary --replicas=10 -n aceest-fitness
kubectl scale deployment aceest-stable --replicas=0 -n aceest-fitness

# Abort canary (if issues found)
kubectl delete deployment aceest-canary -n aceest-fitness
```

### 9.5 Strategy 4 — A/B Testing

```bash
# Deploy variant A and B
kubectl apply -f k8s/ab-testing/variant-a-deployment.yaml -n aceest-fitness
kubectl apply -f k8s/ab-testing/variant-b-deployment.yaml -n aceest-fitness
kubectl apply -f k8s/ab-testing/ingress.yaml -n aceest-fitness

# Verify both variants are running
kubectl get pods -n aceest-fitness -l app=aceest-fitness --show-labels

# Get Minikube IP
minikube ip

# Add to /etc/hosts (Linux/Mac) or C:\Windows\System32\drivers\etc\hosts (Windows)
# <MINIKUBE_IP>  aceest.local

# Test variant routing:
# Default 50/50 split:
curl http://aceest.local/login

# Force Variant B via cookie:
curl -H "Cookie: variant=b" http://aceest.local/login
```

### 9.6 Strategy 5 — Shadow Deployment

```bash
# Deploy production + shadow
kubectl apply -f k8s/shadow/production-deployment.yaml -n aceest-fitness
kubectl apply -f k8s/shadow/shadow-deployment.yaml -n aceest-fitness
kubectl apply -f k8s/shadow/mirror-service.yaml -n aceest-fitness

# Verify both deployments are running
kubectl get deployments -n aceest-fitness

# Production serves real traffic; shadow receives mirrored copy
# Check shadow pod logs to see mirrored requests:
kubectl logs -l track=shadow -n aceest-fitness --tail=20
```

### 9.7 Apply HPA (Autoscaling)

```bash
# Apply HPA (requires metrics-server addon)
kubectl apply -f k8s/hpa.yaml -n aceest-fitness

# Verify HPA is active
kubectl get hpa -n aceest-fitness

# Expected output:
# NAME         REFERENCE                  TARGETS   MINPODS   MAXPODS   REPLICAS
# aceest-hpa   Deployment/aceest-rolling  <5%/70%   2         10        3
```

### 9.8 Get the running cluster endpoint URL

```bash
# Get the Minikube service URL (for submission)
minikube service aceest-service -n aceest-fitness --url

# OR with Ingress:
minikube ip
# Access: http://<MINIKUBE_IP>/login

# OR use port-forward for direct access:
kubectl port-forward svc/aceest-service 5000:80 -n aceest-fitness
# Access: http://localhost:5000/login
```

> 📌 **Save this URL** — it is required for submission.

---

## 10. Step 9 — Configure GitHub Actions Secrets

These secrets enable the `cd.yml` workflow to push to Docker Hub and deploy to your cluster.

1. Go to: https://github.com/phanibitsbyte/aceest-fitness/settings/secrets/actions
2. Click **New repository secret** for each:

| Secret Name | Value |
|---|---|
| `DOCKERHUB_USERNAME` | `phanibitsbyte` |
| `DOCKERHUB_TOKEN` | Your Docker Hub Access Token (from https://hub.docker.com/settings/security) |
| `KUBECONFIG_DATA` | Base64-encoded kubeconfig (see below) |

**Generate KUBECONFIG_DATA:**
```bash
# Linux/Mac
cat ~/.kube/config | base64 -w 0

# Windows PowerShell
[Convert]::ToBase64String([System.IO.File]::ReadAllBytes("$env:USERPROFILE\.kube\config"))
```
Copy the output and paste it as the `KUBECONFIG_DATA` secret value.

---

## 11. Step 10 — Merge develop → main

Once Jenkins is green and Minikube deployments are verified:

### 11.1 Create a Pull Request

1. Go to: https://github.com/phanibitsbyte/aceest-fitness/compare/main...develop
2. Click **Create pull request**
3. Title: `feat: Assignment 2 - Complete CI/CD Pipeline with Kubernetes Deployment Strategies`
4. Description: reference all deliverables
5. Click **Create pull request** → **Merge pull request** → **Confirm merge**

### 11.2 Verify main branch

```bash
git checkout main
git pull origin main
git log --oneline -5
```

### 11.3 Update Jenkins to point to main

1. Jenkins → `aceest-fitness-pipeline` → **Configure**
2. Change branch from `*/develop` to `*/main`
3. Click **Build Now** — confirm all 9 stages are green on main

---

## 12. Submission Checklist

Before submitting, verify every item below:

### Code Repository
- [ ] GitHub repo is **public**: https://github.com/phanibitsbyte/aceest-fitness
- [ ] `main` branch has all Assignment 2 code merged
- [ ] All version files exist: `versions/v1.0/` through `versions/v3.1.2/`
- [ ] Git tags visible: `git tag --list` shows v1.0, v1.1, v2.1.2, v2.2.1, v2.2.4, v3.0.1, v3.1.2, v3.2.4
- [ ] `Jenkinsfile` has all 9 stages
- [ ] `sonar-project.properties` present at repo root
- [ ] `k8s/` directory with all 5 strategy subdirectories
- [ ] `docs/Assignment2-Report.md` present

### Jenkins
- [ ] Jenkins accessible at http://localhost:8080
- [ ] Pipeline `aceest-fitness-pipeline` exists
- [ ] Latest build shows **all stages green** (✅ green ticks)
- [ ] Test Results tab shows passing tests
- [ ] Coverage Report tab shows ≥97% coverage
- [ ] SonarQube Analysis stage completed without errors
- [ ] Docker Hub Push stage shows images pushed

### SonarQube
- [ ] SonarQube accessible at http://localhost:9000
- [ ] Project `aceest-fitness` shows **Passed** Quality Gate
- [ ] 0 Bugs, 0 Vulnerabilities shown (or documented if any)
- [ ] Coverage matches Pytest output

### Docker Hub
- [ ] https://hub.docker.com/r/phanibitsbyte/aceest-fitness/tags shows:
  - [ ] `latest`
  - [ ] `v3.2.4`
  - [ ] `v3.1.2`
  - [ ] `v3.0.1`
  - [ ] `v2.2.4`
  - [ ] `v2.2.1`
  - [ ] `v2.1.2`
  - [ ] `v1.1`
  - [ ] `v1.0`

### Kubernetes Deployments
- [ ] Minikube is running: `minikube status`
- [ ] Namespace exists: `kubectl get ns aceest-fitness`
- [ ] Rolling Update deployment: `kubectl get deploy aceest-rolling -n aceest-fitness`
- [ ] Blue-Green deployments: `kubectl get deploy aceest-blue aceest-green -n aceest-fitness`
- [ ] Canary deployment: `kubectl get deploy aceest-stable aceest-canary -n aceest-fitness`
- [ ] A/B Testing deployments: `kubectl get deploy aceest-variant-a aceest-variant-b -n aceest-fitness`
- [ ] Shadow deployment: `kubectl get deploy aceest-production aceest-shadow -n aceest-fitness`
- [ ] HPA active: `kubectl get hpa -n aceest-fitness`
- [ ] App accessible: `minikube service aceest-service -n aceest-fitness --url`

### Submission Items
- [ ] **GitHub repository URL:** https://github.com/phanibitsbyte/aceest-fitness
- [ ] **Running cluster endpoint URL:** `http://<minikube-ip>:<nodeport>/login`
- [ ] **Jenkins successful build URL:** `http://localhost:8080/job/aceest-fitness-pipeline/lastSuccessfulBuild/`
- [ ] **SonarQube results URL:** `http://localhost:9000/dashboard?id=aceest-fitness`
- [ ] **Docker Hub URL:** https://hub.docker.com/r/phanibitsbyte/aceest-fitness
- [ ] **Report PDF/MD:** `docs/Assignment2-Report.md`

---

## 13. Troubleshooting

### Jenkins "docker: command not found" in pipeline

The Jenkins container needs Docker CLI. Verify the Docker socket is mounted:
```bash
docker exec aceest-jenkins docker ps
```
If it fails, the `docker-compose.yml` `group_add: ["0"]` entry fixes this. Restart:
```bash
docker compose down && docker compose up -d
```

### SonarQube Quality Gate stuck at "In Progress"

The webhook between SonarQube and Jenkins may not be configured. Set it up:
1. SonarQube → **Administration** → **Configuration** → **Webhooks**
2. **Create** → Name: `Jenkins`, URL: `http://jenkins:8080/sonarqube-webhook/`

### Minikube ImagePullBackOff

If pods show `ImagePullBackOff`, the image isn't on Docker Hub yet. Run:
```bash
docker push phanibitsbyte/aceest-fitness:v3.2.4
# OR use minikube's local docker:
eval $(minikube docker-env)
docker build --target production -t phanibitsbyte/aceest-fitness:latest .
# Then set imagePullPolicy to Never in the deployment YAML
```

### kubectl: connection refused (Minikube not running)

```bash
minikube start
kubectl config use-context minikube
kubectl cluster-info
```

### Port 8080 / 9000 already in use

```bash
# Find process using the port (Windows)
netstat -ano | findstr :8080

# Kill it
Stop-Process -Id <PID>

# OR change port in docker-compose.yml
# e.g. "8081:8080" for Jenkins
```

### SonarQube not starting (vm.max_map_count error)

On WSL2/Linux only:
```bash
sudo sysctl -w vm.max_map_count=524288
```

### PVC stuck in Pending state

Minikube's `standard` StorageClass handles PVCs automatically. If stuck:
```bash
kubectl describe pvc aceest-data-pvc -n aceest-fitness
minikube addons enable default-storageclass
minikube addons enable storage-provisioner
```

---

*Document generated for ACEest Fitness & Gym — Assignment 2, BITS Pilani CSIZG514/SEZG514, S1-2025*
