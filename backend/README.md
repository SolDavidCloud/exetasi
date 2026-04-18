# Exetasi backend

FastAPI service for Exetasi. Run locally with uv:

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

Start infrastructure from the repo root with `make infra-up` (Postgres + Valkey), or containerd: `make infra-up COMPOSE='nerdctl compose'`. See the root `README.md` for the full environment setup (`.env.example`, Valkey rate-limit backend, OAuth provider gating).

### Required environment

Copy `.env.example` at the repo root, then symlink or copy the backend subset:

```bash
ln -s ../.env .env
```

Minimum to boot locally:

```env
ENABLE_DEV_AUTH=true
SESSION_SECRET=<long random>
DATABASE_URL=postgresql+asyncpg://exetasi:exetasi@127.0.0.1:5432/exetasi
RATE_LIMIT_STORAGE_URI=memory://   # or redis://:<pw>@127.0.0.1:6379/0
```

For production, `SESSION_SECRET` must be set, `RATE_LIMIT_STORAGE_URI` must point at a Valkey/Redis instance (`memory://` is rejected at startup), and `TRUSTED_PROXY` should be set to `true` **only** if a reverse proxy you control is sanitising `X-Forwarded-For`.

### OAuth (optional)

Set `PUBLIC_API_BASE_URL` to the URL browsers and OAuth providers use to reach this API (e.g. `http://127.0.0.1:8000`). Register these redirect URIs on each provider:

| Provider | Redirect URI |
|----------|----------------|
| GitHub | `{PUBLIC_API_BASE_URL}/api/v1/auth/github/callback` |
| Google | `{PUBLIC_API_BASE_URL}/api/v1/auth/google/callback` |
| GitLab | `{PUBLIC_API_BASE_URL}/api/v1/auth/gitlab/callback` |

Environment variables: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GITLAB_CLIENT_ID`, `GITLAB_CLIENT_SECRET`. For self-managed GitLab, set `GITLAB_OAUTH_BASE_URL` (default `https://gitlab.com`).

Providers with empty credentials are automatically hidden on the login page (via `GET /api/v1/auth/providers`), and the UI shows setup instructions when nothing is configured.

### Rate limiting

`app/core/ratelimit.py` wires [slowapi](https://github.com/laurentS/slowapi) through [limits](https://limits.readthedocs.io/) to a Valkey/Redis backend. Defaults are security-oriented:

- `moving-window` strategy (no burst at window boundaries)
- fail **closed** on storage errors (`RATE_LIMIT_FAIL_OPEN=false`)
- keys namespaced under `exetasi:rl` so a shared Valkey is safe
- `X-Forwarded-For` only honoured when `TRUSTED_PROXY=true`
- a global `default_limits=["600/minute"]` per-IP cap is applied by `SlowAPIMiddleware` to every request

Endpoints stack two `@limiter.limit(...)` decorators — one keyed by IP (`ip_key`), one keyed by hashed session cookie (`user_key`). Unauthenticated requests fall back to the IP bucket automatically. Any function decorated with `@limiter.limit(...)` **must** accept `request: Request` — slowapi inspects the signature.

Tests disable the limiter globally in `tests/conftest.py` (`limiter.enabled = False`) to avoid 127.0.0.1 bucket collisions.

### Audit log

Append-only `audit_logs` table (FKs `ON DELETE SET NULL` so history survives deletions). Writes:

```python
from app.services import audit_service
from app.utils.ip import client_ip

await audit_service.record(
    db,
    action="exam.created",
    actor_user_id=current.id,
    org_id=org.id,
    target_type="exam",
    target_id=exam.id,
    metadata={"name": exam.name},
    ip=client_ip(request),
)
await db.commit()  # caller commits — audit row shares the mutation's tx
```

Reads: `GET /api/v1/audit-log` (self-scoped by default; `?org_slug=…` for org-scoped, owner-only).
