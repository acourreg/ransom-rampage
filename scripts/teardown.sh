#!/bin/bash
set -euo pipefail

echo "💣 Ransom Rampage — Teardown"
echo "============================"
echo "This will destroy ALL AWS resources (EKS, VPC, Cognito, etc.)"
echo "S3 state bucket and Route53 zone will be PRESERVED."
read -p "Type 'destroy' to confirm: " confirm
if [ "$confirm" != "destroy" ]; then
  echo "Aborted."
  exit 0
fi

cd terraform
terraform destroy -auto-approve

echo ""
echo "✅ DESTROYED. Preserved:"
echo "  - S3: ransom-rampage-tfstate"
echo "  - Route53: ransomrampage.com zone"
echo "  - ECR: images preserved"
echo "  - SSM: secrets preserved"
echo ""
echo "To rebuild: terraform apply && ../scripts/deploy.sh"
