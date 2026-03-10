# ACEest Fitness & Gym — DevOps CI/CD Platform

[![CI/CD Pipeline](https://github.com/phanibitsbyte/aceest-fitness-devops/actions/workflows/main.yml/badge.svg?branch=main)](https://github.com/phanibitsbyte/aceest-fitness-devops/actions/workflows/main.yml)

> **Course:** Introduction to DevOps (CSIZG514 / SEZG514 / SEUSZG514) — Assignment 1 · 2026
> **Student:** 2024TM93592 · BITS Pilani WILP

---

## Overview

ACEest Fitness & Gym is a **Python/Flask** web application for managing gym clients, fitness programmes, weekly progress, and workouts. The repository demonstrates a complete, production-grade DevOps workflow covering every stage from version control to containerised CI/CD.

| Area | Technology |
|---|---|
| Application | Python 3.11, Flask 3.0, SQLite |
| Testing | Pytest 8.2, pytest-flask, flake8 |
| Containerisation | Docker (`python:3.11-slim`, multi-stage) |
| Orchestration | Docker Compose (app + Jenkins) |
| CI/CD | GitHub Actions (3-job sequential pipeline) |
| Build Automation | Jenkins (Declarative Pipeline, 5 stages) |
| Version Control | Git / GitHub, `main` + `develop` + `feature/*` |

---

## Quick Start

> Requires: **Docker Desktop** and **Git**. Nothing else needs to be installed locally.

```bash
git clone https://github.com/phanibitsbyte/aceest-fitness-devops.git
cd aceest-fitness
docker compose up -d
```

| Service | URL | Credentials |
|---|---|---|
| Flask web app | http://localhost:5000 | `admin` / `admin` |
| Jenkins CI | http://localhost:8080 | `admin` / `admin` |

To stop everything: `docker compose down`
To wipe all data too: `docker compose down -v`

---

## Features

- Role-based login — **Admin** and **Trainer** roles
- Client CRUD with programme assignment and calorie calculation
- Weekly adherence progress tracking with chart data API
- Workout logging (type, duration, notes, exercises)
- PDF report generation per client (downloadable)
- AI-style fitness programme generator
- Membership expiry management

---

## Project Structure

```
aceest-fitness/
├── app.py                    # Flask application — all routes and DB logic
├── requirements.txt          # Production dependencies (Flask, fpdf2)
├── requirements-dev.txt      # Dev/CI dependencies (pytest, flake8)
│
├── Dockerfile                # Multi-stage: 'test' for CI, 'production' for runtime
├── Dockerfile.jenkins        # Custom Jenkins image (Python 3 + Docker CLI)
├── docker-compose.yml        # Runs Flask app + Jenkins side-by-side
├── .dockerignore
├── .gitattributes            # Enforces LF line endings for all text files
│
├── Jenkinsfile               # Jenkins declarative pipeline (5 stages)
├── jenkins/
│   └── 01-security.groovy    # Groovy init — creates admin user on first boot
│
├── .github/
│   └── workflows/
│       └── main.yml          # GitHub Actions CI/CD pipeline
│
├── templates/                # Jinja2 HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── clients.html
│   ├── client_detail.html
│   ├── workouts.html
│   └── 404.html
│
├── static/
│   └── styles.css            # ACEest dark theme (#1a1a1a, gold #d4af37)
│
└── tests/
    └── test_app.py           # 31 Pytest test cases
```

---

## Local Development (without Docker)

### Prerequisites

- Python 3.11+
- `pip`

### Setup

```bash
git clone https://github.com/phanibitsbyte/aceest-fitness-devops.git
cd aceest-fitness

# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# Install app + dev dependencies
pip install -r requirements-dev.txt

# Start the Flask development server
python app.py
```

Open **http://localhost:5000** — default login: `admin` / `admin`

---

## Running Tests

### Locally

```bash
pytest tests/ -v --tb=short
```

### Inside Docker (mirrors GitHub Actions exactly)

```bash
docker build --target test -t aceest-fitness:test .
docker run --rm aceest-fitness:test
```

Expected: **31 passed**

---

## Docker

### Multi-stage Dockerfile

| Stage | Target flag | Contents | Used by |
|---|---|---|---|
| `test` | `--target test` | Python + all deps + tests | GitHub Actions, local testing |
| `production` | *(default)* | Python + runtime deps only, non-root user | `docker compose`, production |

### Key security / optimisation choices

| Feature | Implementation |
|---|---|
| Non-root user | `appuser` created with `--home /home/appuser` |
| Minimal image | `python:3.11-slim` base |
| Layer caching | Dependencies installed **before** source code is copied |
| Persistent DB | SQLite stored in `/app/data` mounted as a named volume |
| Health check | `GET /login` every 30 s via `HEALTHCHECK` instruction |
| No secrets baked in | `SECRET_KEY` injected at runtime via environment variable |
| Debug mode off | `FLASK_DEBUG=0` hardcoded; reads `os.environ` at `app.run()` |

### Manual build and run

```bash
# Production image
docker build -t aceest-fitness:latest .
docker run -p 5000:5000 -v aceest_data:/app/data aceest-fitness:latest
```

---

## Docker Compose — Full Stack

`docker compose up -d` starts **two services** on a shared `aceest-net` bridge network:

```
┌─────────────────────────────┐   ┌─────────────────────────────┐
│   aceest-fitness-app        │   │   aceest-jenkins             │
│   Flask · port 5000         │   │   Jenkins LTS · port 8080    │
│   Volume: aceest_data       │   │   Volume: jenkins_home       │
│   Health: GET /login        │   │   Docker socket: DooD        │
└─────────────────────────────┘   └─────────────────────────────┘
```

Both containers share the `aceest-net` network, allowing future integration tests to reach the app by its service name (`http://web:5000`).

---

## GitHub Actions Pipeline

**File:** `.github/workflows/main.yml`

**Triggers:** every `push` or `pull_request` to `main`, `develop`, or `feature/**`

```
Push / PR
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  Job 1 · Build & Lint                                │
│  python setup → pip install -r requirements-dev.txt  │
│  flake8 app.py tests/ --max-line-length=120          │
└────────────────────────┬─────────────────────────────┘
                         │ needs: build-and-lint
                         ▼
┌──────────────────────────────────────────────────────┐
│  Job 2 · Docker Image Assembly                       │
│  docker build --target test -t aceest-fitness:ci .   │
└────────────────────────┬─────────────────────────────┘
                         │ needs: docker-build
                         ▼
┌──────────────────────────────────────────────────────┐
│  Job 3 · Automated Testing (Containerised)           │
│  docker run --rm aceest-fitness:test                 │
│  → pytest: 31 tests pass                             │
└──────────────────────────────────────────────────────┘
```

All three jobs must pass for a merge to be allowed.

---

## Jenkins Pipeline

**File:** `Jenkinsfile`

Jenkins acts as a **secondary BUILD quality gate** — an independent validation that the code compiles, lints, tests, and packages correctly outside of GitHub Actions.

### Running Jenkins via Docker Compose

Jenkins is included in `docker-compose.yml` and starts automatically:

```bash
docker compose up -d       # Jenkins available at http://localhost:8080
```

First-time login: `admin` / `admin` (set by `jenkins/01-security.groovy` on first boot).

### Creating the Pipeline job

1. Open **http://localhost:8080** → log in
2. **New Item** → name: `aceest-fitness` → select **Pipeline** → OK
3. Under *Pipeline*: Definition = **Pipeline script from SCM**
4. SCM = **Git**, Repository URL = `https://github.com/phanibitsbyte/aceest-fitness-devops.git`
5. Branch = `*/develop`, Script Path = `Jenkinsfile`
6. **Save** → **Build Now**

### Pipeline stages

```
Checkout → Install Dependencies → Lint → Test → Docker Build
```

| Stage | Command |
|---|---|
| Checkout | `checkout scm` — pulls latest from GitHub |
| Install Dependencies | `python3 -m pip install -r requirements-dev.txt` |
| Lint | `flake8 app.py tests/ --max-line-length=120` |
| Test | `pytest tests/ -v --tb=short` |
| Docker Build | `docker build -t aceest-fitness:<BUILD_NUMBER> .` |

A green `✅ BUILD SUCCESSFUL` banner appears when all five stages pass.

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` / `POST` | `/login` | — | Login / authenticate |
| `GET` | `/logout` | ✓ | Clear session |
| `GET` | `/dashboard` | ✓ | Overview: client list, stats |
| `GET` / `POST` | `/clients` | ✓ | List all clients / add new client |
| `GET` / `POST` | `/clients/<name>` | ✓ | View or update client profile |
| `POST` | `/clients/<name>/progress` | ✓ | Log weekly adherence (%) |
| `GET` / `POST` | `/clients/<name>/workouts` | ✓ | View or log workouts |
| `GET` | `/clients/<name>/report` | ✓ | Download PDF progress report |
| `POST` | `/clients/<name>/generate_program` | ✓ | Generate AI fitness programme |
| `GET` | `/api/clients/<name>/chart` | ✓ | JSON adherence data for charts |

---

## Branching Strategy

```
main           ← production-ready, protected
  └── develop  ← integration branch, all PRs merge here first
        ├── feature/v1-basic-app
        ├── feature/v2-client-management
        └── feature/v3-full-features
```

| Version | Branch | Key additions |
|---|---|---|
| 1.0 – 1.1 | `feature/v1-basic-app` | Flask scaffold, programme display, calorie calculator |
| 2.0 – 2.2 | `feature/v2-client-management` | SQLite DB, client CRUD, progress tracking |
| 3.0 – 3.2 | `feature/v3-full-features` | Login/roles, PDF reports, workout logging |
| CI/CD | `develop` / `main` | Docker, GitHub Actions, Jenkins, tests |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `http://localhost:5000` not loading | Run `docker compose up -d`; check `docker compose logs web` |
| Jenkins shows "Please wait" on first open | It is still booting — wait ~60 s then refresh |
| Jenkins can not run `docker build` | Ensure Docker Desktop is running; check `docker compose logs jenkins` |
| Tests fail locally but pass in Docker | You may have a stale `aceest_fitness.db` — delete it and rerun |
| `SECRET_KEY` warning in logs | Set `SECRET_KEY=<random>` in a `.env` file at the project root |

---

## License

This project is submitted as academic coursework for BITS Pilani WILP.
