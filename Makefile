AWS_REGION   ?= eu-west-1
AWS_ACCOUNT  ?= $(shell aws sts get-caller-identity --query Account --output text)
ECR_BASE     ?= $(AWS_ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com
CLUSTER_NAME ?= ransom-rampage-cluster
TAG          ?= latest

# ── Terraform ───────────────────────────────────────────────
.PHONY: init plan apply destroy

init:
	cd terraform && terraform init

plan:
	cd terraform && terraform plan

apply:
	cd terraform && terraform apply

destroy:
	cd terraform && terraform destroy

# ── Docker ──────────────────────────────────────────────────
.PHONY: build push

build:
	docker build -t api-gateway:$(TAG)  services/api-gateway
	docker build -t dashboard:$(TAG)    services/dashboard

push: build
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_BASE)
	docker tag api-gateway:$(TAG) $(ECR_BASE)/api-gateway:$(TAG)
	docker tag dashboard:$(TAG)   $(ECR_BASE)/dashboard:$(TAG)
	docker push $(ECR_BASE)/api-gateway:$(TAG)
	docker push $(ECR_BASE)/dashboard:$(TAG)

# ── Kubernetes ──────────────────────────────────────────────
.PHONY: smoke

smoke:
	@echo "--- cluster nodes ---"
	kubectl get nodes
	@echo "--- pods ---"
	kubectl get pods -n ransom-rampage
	@echo "--- services ---"
	kubectl get svc -n ransom-rampage

# ── Scripts ─────────────────────────────────────────────────
.PHONY: setup deploy port-forward status teardown

setup:
	@bash scripts/setup.sh

deploy:
	@bash scripts/deploy.sh

port-forward:
	@bash scripts/port-forward.sh

status:
	@bash scripts/status.sh

teardown:
	@bash scripts/teardown.sh

# ── Admin Dashboards ────────────────────────────────────────
.PHONY: grafana argocd-local argocd-password dns-update

grafana:
	@echo "→ Grafana: http://localhost:13001  (admin / prom-operator)"
	kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 13001:80

argocd-local:
	@echo "→ ArgoCD: http://localhost:13002  (admin / <see argocd-password>)"
	kubectl port-forward pod/argocd-proxy -n argocd 13002:8888

argocd-password:
	@kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d && echo

dns-update:
	@echo "Getting ALB DNS..."
	@ALB=$$(kubectl get ingress -n ransom-rampage -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}') && \
	echo "ALB DNS: $$ALB" && \
	echo "Update Route53 manually or run external-dns"
