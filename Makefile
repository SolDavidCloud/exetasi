# Compose CLI for docker-compose.yml. Default matches Docker; override for containerd, e.g.:
#   make db-up COMPOSE='nerdctl compose'
# (Quote the value so Make sees a single assignment.)
COMPOSE ?= docker compose

.PHONY: dev dev-frontend dev-backend test lint codegen install db-up db-down db-verify

install:
	pnpm install
	cd backend && uv sync --extra dev

db-verify:
	@echo 'Compose command: $(COMPOSE)'
	@$(COMPOSE) version

db-up:
	$(COMPOSE) up -d postgres

db-down:
	$(COMPOSE) down

dev-frontend:
	pnpm --dir frontend dev

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev:
	@echo "Run backend and frontend in separate terminals:"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"

test:
	pnpm test
	cd backend && uv run pytest

lint:
	pnpm lint

codegen:
	pnpm codegen
