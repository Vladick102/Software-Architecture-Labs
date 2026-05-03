#!/usr/bin/env bash

set -euo pipefail

echo "==> Pointing Docker CLI to Minikube's daemon..."
eval "$(minikube docker-env)"

echo "==> Building facade-service..."
docker build -t facade-service:latest ./facade-service

echo "==> Building logging-service..."
docker build -t logging-service:latest ./logging-service

echo "==> Building counter-service..."
docker build -t counter-service:latest ./counter-service

echo ""
echo "All images built. Run ./deploy.sh to apply manifests."
