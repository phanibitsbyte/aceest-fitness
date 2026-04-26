#!/bin/bash
# switch-to-green.sh — Cut over traffic from Blue to Green
# Usage: bash scripts/switch-to-green.sh
set -e

NAMESPACE="aceest-fitness"
SERVICE="aceest-bluegreen-svc"

echo "==> Verifying Green deployment is ready..."
kubectl rollout status deployment/aceest-green -n "$NAMESPACE" --timeout=120s

echo "==> Switching service selector to slot=green..."
kubectl patch service "$SERVICE" -n "$NAMESPACE" \
  -p '{"spec":{"selector":{"app":"aceest-fitness","slot":"green"}}}'

echo "✅ Traffic now routed to GREEN (v3.1.2)"
echo "   To rollback, run: bash scripts/rollback-to-blue.sh"
