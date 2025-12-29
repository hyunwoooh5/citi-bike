IMAGE_NAME = citi-bike
TAG = v1
KIND_CLUSTER = citi-bike-cluster
PYTHON = uv run python

MONTH ?= 3


.PHONY: setup check fix train test run-local monitor-up monitor-down monitor-backfill docker-build docker-rmi k8s-up k8s-down deploy-lambda help

setup: ## Install project dependencies using uv
	curl -LsSf https://astral.sh/uv/install.sh | sh
	uv sync --locked --extra workflows

check: ## Check for linting errors and import sorting without applying changes
	uv run ruff check .
	uv run ruff format --check .

fix: ## Automatically fix linting errors and reformat code
	uv run ruff check --fix .
	uv run ruff format .


train: ## Run Prefect training flow and register the champion model
	$(PYTHON) flows/train_flow.py "data/2024_top3.csv"

test: ## Run unit tests
	uv run pytest tests/

run-local: ## Start the FastAPI server locally
	$(PYTHON) src/serve.py

monitor-up: ## Start monitoring infrastructure (PostgreSQL, Grafana)
	docker-compose up -d

monitor-down: ## Stop monitoring infrastructure
	docker-compose down

monitor-backfill: ## Run monitoring backfill with MONTH (default=3)
	$(PYTHON) flows/monitoring_data_flow.py $(MONTH)
	$(PYTHON) flows/monitoring_performance_flow.py $(MONTH)


docker-build: ## Build the service Docker image
	docker build -t $(IMAGE_NAME):$(TAG) .

docker-rmi: ## Remove the service docker image
	docker rmi $(IMAGE_NAME):$(TAG)

k8s-up: docker-build ## Create Kind cluster and deploy resources
	kind create cluster --name $(KIND_CLUSTER) || true
	kind load docker-image $(IMAGE_NAME):$(TAG) --name $(KIND_CLUSTER)
	kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
	kubectl patch deployment metrics-server -n kube-system --type='json' \
		-p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'
	kubectl apply -f k8s/

k8s-down: ## Delete the Kind cluster
	kind delete cluster --name $(KIND_CLUSTER)


deploy-lambda: ## Build and push image to AWS ECR, then update Lambda
	chmod +x deploy_lambda.sh
	./deploy_lambda.sh	


help: ## Display this help message
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'