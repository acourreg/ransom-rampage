resource "aws_elasticache_cluster" "ransom_rampage" {
  cluster_id = "cluster-ransom-rampage"
  engine                = "redis"
  
  node_type            = "cache.t2.micro"
  num_cache_nodes      = 1
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.elasticache_private_subnet_binding.name
}

resource "aws_elasticache_subnet_group" "elasticache_private_subnet_binding" {
  name       = "elasticache-private-subnet-binding"
  subnet_ids = var.private_subnet_ids
}