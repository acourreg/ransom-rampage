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