#!/bin/bash
set -euo pipefail

echo "🚀 Ransom Rampage — Post-Terraform Deploy"
echo "==========================================="

# Prerequisites check
for cmd in aws kubectl helm terraform; do
  command -v $cmd >/dev/null 2>&1 || { echo "❌ $cmd not found"; exit 1; }
done

# 1. Update kubeconfig
echo "📡 Updating kubeconfig..."
CLUSTER_NAME=$(cd terraform && terraform output -raw cluster_name 2>/dev/null || echo "ransom-rampage-cluster")
REGION=${AWS_REGION:-eu-west-1}
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$REGION"

# 2. Wait for nodes
echo "⏳ Waiting for nodes..."
kubectl wait --for=condition=Ready nodes --all --timeout=120s

# 3. Read terraform outputs
echo "📋 Reading terraform outputs..."
cd terraform
ACM_ARN=$(terraform output -raw acm_certificate_arn)
POOL_ARN=$(terraform output -raw cognito_user_pool_arn)
POOL_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)
ECR_API=$(terraform output -raw ecr_api_gateway_url 2>/dev/null || echo "$(terraform output -json repo_urls | python3 -c 'import sys,json; print(json.load(sys.stdin).get("api-gateway","MISSING"))')")
ECR_DASH=$(terraform output -raw ecr_dashboard_url 2>/dev/null || echo "$(terraform output -json repo_urls | python3 -c 'import sys,json; print(json.load(sys.stdin).get("dashboard","MISSING"))')")
cd ..

# 4. Patch K8s manifests with real values
echo "🔧 Patching K8s manifests with terraform outputs..."
for f in k8s/ingress/ingress-protected.yaml k8s/ingress/ingress-public.yaml; do
  sed -i.bak "s|__ACM_CERTIFICATE_ARN__|${ACM_ARN}|g" "$f"
done
sed -i.bak "s|__COGNITO_USER_POOL_ARN__|${POOL_ARN}|g" k8s/ingress/ingress-protected.yaml
sed -i.bak "s|__COGNITO_USER_POOL_CLIENT_ID__|${POOL_CLIENT_ID}|g" k8s/ingress/ingress-protected.yaml
sed -i.bak "s|__ECR_API_GATEWAY_URL__|${ECR_API}|g" k8s/argocd/application.yaml
sed -i.bak "s|__ECR_DASHBOARD_URL__|${ECR_DASH}|g" k8s/argocd/application.yaml

# Clean backup files
find k8s/ -name "*.bak" -delete

# 5. Install ESO if not present
if ! kubectl get namespace external-secrets >/dev/null 2>&1; then
  echo "📦 Installing External Secrets Operator..."
  helm repo add external-secrets https://charts.external-secrets.io 2>/dev/null || true
  helm install external-secrets external-secrets/external-secrets \
    --namespace external-secrets --create-namespace
  sleep 10
fi

# 6. Apply manifests in order
echo "📦 Applying K8s manifests..."
kubectl apply -f k8s/namespaces/
sleep 2
kubectl apply -f k8s/secrets/ 2>/dev/null || echo "⚠️  Secrets may need ESO CRDs — retrying in 10s..."
sleep 10
kubectl apply -f k8s/secrets/ 2>/dev/null || true
kubectl apply -f k8s/ingress/
kubectl apply -f k8s/argocd/
kubectl apply -f k8s/monitoring/servicemonitor.yaml 2>/dev/null || true
kubectl apply -f k8s/monitoring/grafana-dashboard-configmap.yaml 2>/dev/null || true

# 7. Wait for pods
echo "⏳ Waiting for pods..."
kubectl wait --for=condition=Ready pods --all -n ransom-rampage --timeout=120s 2>/dev/null || true

# 8. Get ALB DNS
echo "⏳ Waiting for ALB provisioning (up to 3 min)..."
ALB_DNS=""
for i in $(seq 1 18); do
  ALB_DNS=$(kubectl get ingress -n ransom-rampage -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
  if [ -n "$ALB_DNS" ]; then break; fi
  sleep 10
done

# 9. Restore PLACEHOLDERs in git (don't commit real values)
echo "🔄 Restoring PLACEHOLDERs in manifests (git-clean)..."
git checkout -- k8s/

echo ""
echo "✅ DEPLOY COMPLETE"
echo "==================="
echo "ALB DNS:    ${ALB_DNS:-PENDING}"
echo "Dashboard:  https://ransomrampage.com"
echo "API:        https://ransomrampage.com/health"
echo ""
echo "⚠️  If ALB DNS changed, update Route53:"
echo "   Run: make dns-update"
