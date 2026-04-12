.PHONY: dev dev-frontend dev-backend test lint codegen install db-up db-down

install:
	pnpm install
	cd backend && uv sync --extra dev

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

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
