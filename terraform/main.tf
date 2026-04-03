module "networking" {
  source       = "./modules/networking"
  vpc_cidr     = var.vpc_cidr
  subnet_cidrs = var.subnet_cidrs
  azs          = var.availability_zones
}

module "eks" {
  source             = "./modules/eks"
  cluster_name       = var.cluster_name
  private_subnet_ids = module.networking.private_subnet_ids  # ← output networking → input eks
  vpc_id             = module.networking.vpc_id
}

module "ecr" {
  source             = "./modules/ecr"
  services           = var.services
}

module "data" {
  source             = "./modules/data"
  private_subnet_ids = module.networking.private_subnet_ids  # ← output networking → input eks
}

module "config" {
  source             = "./modules/config"
  redis_endpoint     = module.data.redis_endpoint
}


