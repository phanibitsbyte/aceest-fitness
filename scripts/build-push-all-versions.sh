#!/bin/bash
# build-push-all-versions.sh
# Builds and pushes all ACEest version images to Docker Hub.
# Usage: bash scripts/build-push-all-versions.sh
# Requires: DOCKERHUB_USER and DOCKERHUB_PASS env vars, or logged in via `docker login`.
set -e

REPO="phanibitsbyte/aceest-fitness"

echo "==> Logging in to Docker Hub..."
if [ -n "$DOCKERHUB_PASS" ]; then
    echo "$DOCKERHUB_PASS" | docker login -u "${DOCKERHUB_USER:-phanibitsbyte}" --password-stdin
fi

# Version map: tag => versions/<dir>
declare -A VERSIONS=(
    ["v1.0"]="versions/v1.0"
    ["v1.1"]="versions/v1.1"
    ["v2.1.2"]="versions/v2.1.2"
    ["v2.2.1"]="versions/v2.2.1"
    ["v2.2.4"]="versions/v2.2.4"
    ["v3.0.1"]="versions/v3.0.1"
    ["v3.1.2"]="versions/v3.1.2"
    ["v3.2.4"]="."           # latest full version = repo root
)

for TAG in "${!VERSIONS[@]}"; do
    DIR="${VERSIONS[$TAG]}"
    echo ""
    echo "==> Building ${REPO}:${TAG} from ${DIR}/"

    if [ "$DIR" = "." ]; then
        # Full production image from repo root
        docker build --target production -t "${REPO}:${TAG}" .
    else
        # Simple single-stage build for version directories
        docker build -f - "${DIR}" <<EOF
FROM python:3.11-slim
RUN adduser --disabled-password --gecos "" --home /home/appuser appuser
WORKDIR /app
COPY requirements.txt . 2>/dev/null || echo "flask\nfpdf2" > requirements.txt
RUN pip install --no-cache-dir flask fpdf2
COPY app.py .
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 5000
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["python", "app.py"]
EOF
        docker tag "${REPO}:${TAG}" "${REPO}:${TAG}"
    fi

    echo "==> Pushing ${REPO}:${TAG}..."
    docker push "${REPO}:${TAG}"
    echo "✅ ${REPO}:${TAG} pushed."
done

# Also tag latest as v3.2.4
docker tag "${REPO}:v3.2.4" "${REPO}:latest"
docker push "${REPO}:latest"

echo ""
echo "✅ All versions pushed to Docker Hub:"
for TAG in "${!VERSIONS[@]}"; do
    echo "   https://hub.docker.com/r/phanibitsbyte/aceest-fitness/tags?name=${TAG}"
done

docker logout
