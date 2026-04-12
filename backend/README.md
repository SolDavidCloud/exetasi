# Exetasi backend

FastAPI service for Exetasi. Run locally with uv or pip:

```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Tests:

```bash
uv run pytest
```

Set `DATABASE_URL` for PostgreSQL (see root `docker-compose.yml`). For tests, `DATABASE_URL` defaults to the same compose URL if unset.
