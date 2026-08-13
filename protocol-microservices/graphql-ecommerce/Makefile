# =============================================================================
# GraphQL e-commerce — developer shortcuts.
# On Windows, run these under Git Bash / WSL, or invoke the commands directly.
# =============================================================================
.DEFAULT_GOAL := help
PYTHON ?= .venv/Scripts/python.exe   # on Linux/macOS use .venv/bin/python

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: up
up: ## Build and start the whole stack in the background
	docker compose up --build -d

.PHONY: down
down: ## Stop the stack and remove volumes
	docker compose down -v

.PHONY: logs
logs: ## Tail logs from all services
	docker compose logs -f

.PHONY: ps
ps: ## Show running containers
	docker compose ps

.PHONY: test
test: ## Run every service + gateway test suite
	cd services/users    && ../../$(PYTHON) -m pytest -q
	cd services/products && ../../$(PYTHON) -m pytest -q
	cd services/orders   && ../../$(PYTHON) -m pytest -q
	cd gateway           && ../$(PYTHON) -m pytest -q
