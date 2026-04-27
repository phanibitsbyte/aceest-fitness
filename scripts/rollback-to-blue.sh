#!/bin/bash
# rollback-to-blue.sh — Rollback traffic from Green back to Blue
# Usage: bash scripts/rollback-to-blue.sh
set -e

NAMESPACE="aceest-fitness"
SERVICE="aceest-bluegreen-svc"

echo "==> Switching service selector back to slot=blue..."
kubectl patch service "$SERVICE" -n "$NAMESPACE" \
  -p '{"spec":{"selector":{"app":"aceest-fitness","slot":"blue"}}}'

echo "✅ Traffic rolled back to BLUE (v3.2.4)"
