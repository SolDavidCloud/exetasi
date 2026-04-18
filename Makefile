# Compose CLI for docker-compose.yml. Default matches Docker; override for containerd, e.g.:
#   make db-up COMPOSE='nerdctl compose'
# (Quote the value so Make sees a single assignment.)
COMPOSE ?= docker compose

.PHONY: dev dev-frontend dev-backend test lint codegen install \
        db-up db-down db-verify valkey-up valkey-down infra-up infra-down

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

# Valkey (rate-limit backend). Requires VALKEY_PASSWORD in .env — compose
# will refuse to start without one.
valkey-up:
	$(COMPOSE) up -d valkey

valkey-down:
	$(COMPOSE) stop valkey

# Convenience: bring up both dependencies in one command.
infra-up: db-up valkey-up

infra-down:
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
