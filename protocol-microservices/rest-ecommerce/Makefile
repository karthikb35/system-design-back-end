# =============================================================================
# Developer shortcuts for the REST e-commerce system.
# Usage: `make <target>`  (run `make help` to list targets)
# =============================================================================
.DEFAULT_GOAL := help
SERVICES := services/users services/products services/orders gateway

.PHONY: help up down logs ps build restart test clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	 awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## Build + start the whole system in the background
	docker compose up --build -d

down: ## Stop and remove all containers
	docker compose down

logs: ## Tail logs from all services
	docker compose logs -f

ps: ## Show running containers
	docker compose ps

build: ## Build all images without starting
	docker compose build

restart: ## Restart all services
	docker compose restart

test: ## Run the pytest suite in every service
	@for svc in $(SERVICES); do \
		echo "==> testing $$svc"; \
		(cd $$svc && python -m pytest -q) || exit 1; \
	done

clean: ## Stop everything and delete the database volume
	docker compose down -v
