#!/bin/bash
set -euo pipefail

echo "🔧 Ransom Rampage — First-Time Setup"
echo "======================================"

# Prerequisites
for cmd in aws terraform kubectl helm; do
  command -v $cmd >/dev/null 2>&1 || { echo "❌ Install $cmd first"; exit 1; }
done

REGION=${AWS_REGION:-eu-west-1}

# 1. S3 backend
echo "📦 Creating S3 state bucket (if not exists)..."
aws s3 mb s3://ransom-rampage-tfstate --region "$REGION" 2>/dev/null || echo "  Already exists"

# 2. SSM parameters (prompt for values)
echo ""
echo "📋 SSM Parameters"
if ! aws ssm get-parameter --name "/ransom-rampage/openai-api-key" --region "$REGION" >/dev/null 2>&1; then
  read -sp "Enter OpenAI API Key: " OPENAI_KEY
  echo ""
  aws ssm put-parameter --name "/ransom-rampage/openai-api-key" --value "$OPENAI_KEY" --type SecureString --region "$REGION"
  echo "  ✅ OpenAI key stored"
else
  echo "  ✅ OpenAI key already in SSM"
fi

if ! aws ssm get-parameter --name "/ransom-rampage/google-client-id" --region "$REGION" >/dev/null 2>&1; then
  read -p "Enter Google OAuth Client ID: " GOOGLE_ID
  aws ssm put-parameter --name "/ransom-rampage/google-client-id" --value "$GOOGLE_ID" --type SecureString --region "$REGION"
  read -sp "Enter Google OAuth Client Secret: " GOOGLE_SECRET
  echo ""
  aws ssm put-parameter --name "/ransom-rampage/google-client-secret" --value "$GOOGLE_SECRET" --type SecureString --region "$REGION"
  echo "  ✅ Google OAuth stored"
else
  echo "  ✅ Google OAuth already in SSM"
fi

# 3. Terraform init
echo ""
echo "🏗️  Terraform init..."
cd terraform
terraform init

echo ""
echo "✅ SETUP COMPLETE"
echo "Next steps:"
echo "  1. cp terraform/terraform.tfvars.example terraform/terraform.tfvars"
echo "  2. Edit terraform/terraform.tfvars with your AWS account ID"
echo "  3. cd terraform && terraform plan"
echo "  4. terraform apply"
echo "  5. ../scripts/deploy.sh"
