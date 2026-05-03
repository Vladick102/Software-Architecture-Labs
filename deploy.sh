#!/usr/bin/env bash

set -euo pipefail

echo "==> Applying manifests..."
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-configmap.yaml
kubectl apply -f k8s/02-mongodb.yaml
kubectl apply -f k8s/03-hazelcast.yaml

echo "==> Waiting for Hazelcast StatefulSet to be ready..."
kubectl rollout status statefulset/hazelcast -n bank --timeout=120s

kubectl apply -f k8s/04-logging-service.yaml
kubectl apply -f k8s/05-counter-service.yaml
kubectl apply -f k8s/06-facade-service.yaml

echo ""
echo "==> All manifests applied. Checking pods..."
kubectl get pods -n bank

echo ""
MINIKUBE_IP=$(minikube ip 2>/dev/null || echo "<minikube-ip>")
echo "==> Facade Service available at: http://${MINIKUBE_IP}:30080"
echo "    Or run:  minikube service facade-service -n bank --url"
