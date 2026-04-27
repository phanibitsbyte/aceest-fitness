#!/bin/bash
# rollback.sh — Generic rollback using kubectl rollout undo
# Usage: bash scripts/rollback.sh [deployment-name] [namespace]
set -e

DEPLOYMENT="${1:-aceest-rolling}"
NAMESPACE="${2:-aceest-fitness}"

echo "==> Rolling back deployment/$DEPLOYMENT in namespace $NAMESPACE..."
kubectl rollout undo deployment/"$DEPLOYMENT" -n "$NAMESPACE"

echo "==> Waiting for rollback to complete..."
kubectl rollout status deployment/"$DEPLOYMENT" -n "$NAMESPACE" --timeout=120s

echo "✅ Rollback complete for $DEPLOYMENT"
kubectl get pods -n "$NAMESPACE" -l app=aceest-fitness
