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

Start Postgres from the repo root with `make db-up`, or with containerd: `make db-up COMPOSE='nerdctl compose'` (see root `README.md`).

### OAuth (optional)

Set `PUBLIC_API_BASE_URL` to the URL browsers and OAuth providers use to reach this API (e.g. `http://127.0.0.1:8000`). Register these redirect URIs on each provider:

| Provider | Redirect URI |
|----------|----------------|
| GitHub | `{PUBLIC_API_BASE_URL}/api/v1/auth/github/callback` |
| Google | `{PUBLIC_API_BASE_URL}/api/v1/auth/google/callback` |
| GitLab | `{PUBLIC_API_BASE_URL}/api/v1/auth/gitlab/callback` |

Environment variables: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GITLAB_CLIENT_ID`, `GITLAB_CLIENT_SECRET`. For self-managed GitLab, set `GITLAB_OAUTH_BASE_URL` (default `https://gitlab.com`).
