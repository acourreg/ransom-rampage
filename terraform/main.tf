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

module "cognito" {
  source               = "./modules/cognito"
  google_client_id     = module.config.google_client_id
  google_client_secret = module.config.google_client_secret
}

resource "helm_release" "aws_lb_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"

  set {
    name  = "clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "serviceAccount.create"
    value = "true"
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.eks.alb_controller_role_arn
  }

  depends_on = [module.eks, aws_acm_certificate_validation.cert]
}

resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = "7.8.23"
  namespace        = "argocd"
  create_namespace = true

  set {
    name  = "server.service.type"
    value = "ClusterIP"
  }

  set {
    name  = "configs.params.server\\.insecure"
    value = "true"
  }

  depends_on = [module.eks]
}
