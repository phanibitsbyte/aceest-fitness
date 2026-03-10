# ============================================================
# ACEest Fitness & Gym – Dockerfile
# Multi-stage build:
#   Stage 1 (test)       – includes dev tools; used by CI to run Pytest
#   Stage 2 (production) – lean image, runtime deps only, non-root user
#
# Build targets:
#   CI testing:  docker build --target test -t aceest-fitness:test .
#   Production:  docker build -t aceest-fitness:latest .
# ============================================================

# ── Stage 1: test ────────────────────────────────────────────
FROM python:3.11-slim AS test

# Security: non-root user with explicit home directory
RUN adduser --disabled-password --gecos "" --home /home/appuser appuser

WORKDIR /app

# Make /app writable by appuser so pytest can create the test DB file
RUN chown appuser:appuser /app

# Layer-cache optimisation: install deps before copying source
# requirements.txt must be present because requirements-dev.txt references it via -r
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements-dev.txt

# Copy source with correct ownership in one layer (no separate chown RUN)
COPY --chown=appuser:appuser . .

USER appuser

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_NAME=test_aceest.db

CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]


# ── Stage 2: production ──────────────────────────────────────
FROM python:3.11-slim AS production

# Security: non-root user with explicit home directory
RUN adduser --disabled-password --gecos "" --home /home/appuser appuser

WORKDIR /app

# Install only runtime dependencies — no test tools in production image
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy only the application source (no tests, no CI config)
COPY --chown=appuser:appuser app.py .
COPY --chown=appuser:appuser templates/ templates/
COPY --chown=appuser:appuser static/ static/

# Dedicated writable directory for the SQLite database (mounted as a volume)
RUN mkdir -p /app/data && chown appuser:appuser /app/data

USER appuser

# Flask listens on 5000
EXPOSE 5000

ENV FLASK_DEBUG=0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_NAME=/app/data/aceest_fitness.db
# SECRET_KEY must be injected at runtime — never hardcode in production:
#   docker run -e SECRET_KEY=<strong-random-value> aceest-fitness:latest

# Persist the SQLite database across container restarts
VOLUME ["/app/data"]

# Health check: hit /login (no auth required) every 30s
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/login')" || exit 1

CMD ["python", "app.py"]

