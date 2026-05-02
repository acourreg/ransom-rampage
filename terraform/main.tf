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

  set {
    name  = "vpcId"
    value = module.networking.vpc_id
  }

  set {
    name  = "region"
    value = var.aws_region
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

resource "helm_release" "kube_prometheus_stack" {
  name             = "kube-prometheus-stack"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = "72.6.2"
  namespace        = "monitoring"
  create_namespace = true

  # Reduce resource usage for portfolio (t3.medium = 4GB RAM)
  set {
    name  = "prometheus.prometheusSpec.resources.requests.memory"
    value = "256Mi"
  }
  set {
    name  = "prometheus.prometheusSpec.resources.limits.memory"
    value = "512Mi"
  }
  set {
    name  = "prometheus.prometheusSpec.retention"
    value = "3d"
  }
  set {
    name  = "grafana.resources.requests.memory"
    value = "128Mi"
  }
  set {
    name  = "grafana.resources.limits.memory"
    value = "256Mi"
  }
  # Disable components we don't need (save RAM)
  set {
    name  = "alertmanager.enabled"
    value = "false"
  }

  # Loki as additional data source in Grafana
  set {
    name  = "grafana.additionalDataSources[0].name"
    value = "Loki"
  }
  set {
    name  = "grafana.additionalDataSources[0].type"
    value = "loki"
  }
  set {
    name  = "grafana.additionalDataSources[0].url"
    value = "http://loki-stack:3100"
  }
  set {
    name  = "grafana.additionalDataSources[0].access"
    value = "proxy"
  }

  depends_on = [module.eks]
}

resource "helm_release" "loki_stack" {
  name             = "loki-stack"
  repository       = "https://grafana.github.io/helm-charts"
  chart            = "loki-stack"
  version          = "2.10.2"
  namespace        = "monitoring"
  create_namespace = false  # already created by kube-prometheus-stack

  # Enable Promtail (log collector, DaemonSet = 1 per node)
  set {
    name  = "promtail.enabled"
    value = "true"
  }

  # Loki resource limits (lightweight — labels-only indexing)
  set {
    name  = "loki.resources.requests.memory"
    value = "128Mi"
  }
  set {
    name  = "loki.resources.limits.memory"
    value = "256Mi"
  }

  # Retention — 3 days for portfolio
  set {
    name  = "loki.config.table_manager.retention_deletes_enabled"
    value = "true"
  }
  set {
    name  = "loki.config.table_manager.retention_period"
    value = "72h"
  }

  depends_on = [helm_release.kube_prometheus_stack]
}
