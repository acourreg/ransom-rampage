output "redis_endpoint" {
  value = aws_elasticache_cluster.ransom_rampage.cache_nodes[0].address
}