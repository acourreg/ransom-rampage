output "cluster_name"     { value = aws_eks_cluster.ransom_rampage_cluster.name }
output "cluster_endpoint" { value = aws_eks_cluster.ransom_rampage_cluster.endpoint }
output "cluster_ca" {
  value = aws_eks_cluster.ransom_rampage_cluster.certificate_authority[0].data
}