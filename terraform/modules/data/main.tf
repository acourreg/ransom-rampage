resource "aws_security_group" "redis" {
  name        = "ransom-rampage-redis"
  description = "Allow Redis access from VPC"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_cluster" "ransom_rampage" {
  cluster_id         = "cluster-ransom-rampage"
  engine             = "redis"
  node_type          = "cache.t3.micro"
  num_cache_nodes    = 1
  port               = 6379
  subnet_group_name  = aws_elasticache_subnet_group.elasticache_private_subnet_binding.name
  security_group_ids = [aws_security_group.redis.id]
}

resource "aws_elasticache_subnet_group" "elasticache_private_subnet_binding" {
  name       = "elasticache-private-subnet-binding"
  subnet_ids = var.private_subnet_ids
}