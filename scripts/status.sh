#!/bin/bash
echo "📊 Ransom Rampage — Status"
echo "=========================="

echo ""
echo "🟢 NODES"
kubectl get nodes -o wide 2>/dev/null || echo "❌ Cannot reach cluster"

echo ""
echo "🟢 PODS"
kubectl get pods -n ransom-rampage 2>/dev/null || echo "❌ No pods"

echo ""
echo "🟢 INGRESS"
kubectl get ingress -n ransom-rampage 2>/dev/null || echo "❌ No ingress"

echo ""
echo "🟢 HEALTH"
curl -s -o /dev/null -w "API /health: %{http_code}\n" https://ransomrampage.com/health 2>/dev/null || echo "❌ API unreachable"
curl -s -o /dev/null -w "Dashboard:   %{http_code}\n" https://ransomrampage.com 2>/dev/null || echo "❌ Dashboard unreachable"

echo ""
echo "🟢 MONITORING"
kubectl get pods -n monitoring --no-headers 2>/dev/null | awk '{printf "  %-50s %s\n", $1, $3}'

echo ""
echo "🟢 ARGOCD"
kubectl get applications -n argocd 2>/dev/null || echo "❌ No ArgoCD apps"
