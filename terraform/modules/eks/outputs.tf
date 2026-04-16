output "cluster_name"     { value = aws_eks_cluster.ransom_rampage_cluster.name }
output "cluster_endpoint" { value = aws_eks_cluster.ransom_rampage_cluster.endpoint }
output "cluster_ca" {
  value = aws_eks_cluster.ransom_rampage_cluster.certificate_authority[0].data
}

output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.eks.arn
}

output "eso_role_arn" {
  description = "Annotate ESO service account with this ARN"
  value       = aws_iam_role.eso_role.arn
}