#!/bin/bash
echo "🔌 Starting port-forwards..."

pkill -f "port-forward" 2>/dev/null || true
sleep 1

# Grafana
kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 13001:80 &>/dev/null &

# ArgoCD (via proxy pod if direct port-forward fails)
if kubectl get pod argocd-proxy -n argocd >/dev/null 2>&1; then
  kubectl port-forward pod/argocd-proxy -n argocd 13002:8888 &>/dev/null &
else
  kubectl port-forward deploy/argocd-server -n argocd 13002:8080 &>/dev/null &
fi

# Prometheus
kubectl port-forward svc/kube-prometheus-stack-prometheus -n monitoring 13003:9090 &>/dev/null &

# K8s Dashboard (if installed)
if kubectl get svc kubernetes-dashboard -n kubernetes-dashboard >/dev/null 2>&1; then
  kubectl port-forward svc/kubernetes-dashboard -n kubernetes-dashboard 13005:443 &>/dev/null &
fi

sleep 3

ARGOCD_PASS=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d || echo "N/A")

echo ""
echo "📊 DASHBOARDS"
echo "=============="
echo "Grafana:      http://localhost:13001    admin / prom-operator"
echo "ArgoCD:       http://localhost:13002    admin / ${ARGOCD_PASS}"
echo "Prometheus:   http://localhost:13003"
echo "K8s Dashboard: https://localhost:13005  (token auth)"
echo ""
echo "Stop all: pkill -f port-forward"
