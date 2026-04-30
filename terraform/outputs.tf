# ── EKS ─────────────────────────────────────────────────────
output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "cluster_ca" {
  value     = module.eks.cluster_ca
  sensitive = true
}

# ── ECR ─────────────────────────────────────────────────────
output "repo_urls" {
  value = module.ecr.repo_urls
}

# ── Data ────────────────────────────────────────────────────
output "redis_endpoint" {
  value = module.data.redis_endpoint
}

# ── DNS / TLS ──────────────────────────────────────────────
output "acm_certificate_arn" {
  value       = aws_acm_certificate_validation.cert.certificate_arn
  description = "ACM certificate ARN — use in Ingress annotation"
}

# ── Cognito ─────────────────────────────────────────────────
output "cognito_user_pool_arn" {
  value = module.cognito.user_pool_arn
}

output "cognito_user_pool_client_id" {
  value = module.cognito.user_pool_client_id
}

output "cognito_user_pool_domain" {
  value = module.cognito.user_pool_domain
}