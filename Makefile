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
	docker build -t api_gateway:$(TAG)  services/api-gateway
	docker build -t dashboard:$(TAG)    services/dashboard

push: build
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_BASE)
	docker tag api_gateway:$(TAG) $(ECR_BASE)/api_gateway:$(TAG)
	docker tag dashboard:$(TAG)   $(ECR_BASE)/dashboard:$(TAG)
	docker push $(ECR_BASE)/api_gateway:$(TAG)
	docker push $(ECR_BASE)/dashboard:$(TAG)

# ── Kubernetes ──────────────────────────────────────────────
.PHONY: deploy password smoke

deploy:
	aws eks update-kubeconfig --name $(CLUSTER_NAME) --region $(AWS_REGION)
	kubectl apply -f k8s/

password:
	aws eks update-kubeconfig --name $(CLUSTER_NAME) --region $(AWS_REGION)

smoke:
	@echo "--- cluster nodes ---"
	kubectl get nodes
	@echo "--- pods ---"
	kubectl get pods -n ransom-rampage
	@echo "--- services ---"
	kubectl get svc -n ransom-rampage