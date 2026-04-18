# exetasi (exetasi)

Free quiz and exam webapp (monorepo: Quasar frontend + FastAPI backend).

Implementation plan: [docs/plans/exetasi-implementation-plan.md](docs/plans/exetasi-implementation-plan.md).

## Prerequisites

- [Node.js](https://nodejs.org/) 22+ and [pnpm](https://pnpm.io/) 10+
- [uv](https://docs.astral.sh/uv/) (Python 3.12+)
- **PostgreSQL + Valkey via Compose** — either:
  - [Docker](https://docs.docker.com/get-docker/) with Compose (`docker compose`), or
  - [containerd](https://containerd.io/) + [nerdctl](https://github.com/containerd/nerdctl) with the Compose subcommand (`nerdctl compose`; needs CNI for published ports)

Check your Compose CLI: `make db-verify` (Docker) or `make db-verify COMPOSE='nerdctl compose'` (nerdctl).

## Install

From the repository root:

```bash
pnpm install
cd backend && uv sync --extra dev
```

## Environment

Copy `.env.example` and fill in the secrets **before** bringing the stack up — Compose refuses to start Valkey without a `VALKEY_PASSWORD`, and `get_settings()` refuses to boot the backend in production without a real `SESSION_SECRET`.

```bash
cp .env.example .env
# Generate strong, unique values:
python -c "import secrets; print('VALKEY_PASSWORD='  + secrets.token_urlsafe(48))" >> .env
python -c "import secrets; print('SESSION_SECRET=' + secrets.token_urlsafe(48))" >> .env
```

The backend reads `backend/.env` if present (in addition to the process environment). For dev you can symlink: `ln -s ../.env backend/.env`.

`.env` is gitignored; `.env.example` is the template and the single source of truth for which variables exist — keep it in sync when adding new settings.

## Infrastructure (local)

Two Compose services: **PostgreSQL** (primary data) and **Valkey** (shared rate-limit counters). The Makefile uses `docker compose` unless you override `COMPOSE`.

```bash
make infra-up          # postgres + valkey
cd backend && uv run alembic upgrade head
```

Individual services:

```bash
make db-up             # postgres only
make valkey-up         # valkey only
make db-down           # or `make infra-down` / `make valkey-down`
```

**containerd + nerdctl:** same `docker-compose.yml`, pass Compose explicitly (quote the value so Make treats it as one assignment):

```bash
make infra-up COMPOSE='nerdctl compose'
make infra-down COMPOSE='nerdctl compose'
make db-verify COMPOSE='nerdctl compose'
```

PostgreSQL credentials and port match `docker-compose.yml`: user, password, and database **`exetasi`**, host **`127.0.0.1`**, port **`5432`**. Valkey listens on **`127.0.0.1:6379`** and requires the `VALKEY_PASSWORD` from your `.env`.

Both ports are bound to loopback by design — nothing is reachable from the LAN.

## Develop

Run the infrastructure (`make infra-up`), apply migrations, then start **backend** and **frontend** in two terminals:

```bash
make dev-backend
```

```bash
make dev-frontend
```

The Quasar dev server proxies `/api` to `http://127.0.0.1:8000` so the SPA and API share one origin in development (cookies work as first-party).

### Rate limiting (Valkey)

All mutating endpoints and the auth flow are rate-limited via [slowapi](https://github.com/laurentS/slowapi) with a [Valkey](https://valkey.io/) backend (Redis-compatible; `redis://` URIs are accepted). Three layers are in effect:

1. A global **600/minute per-IP** soft ceiling from `SlowAPIMiddleware`.
2. A **per-IP** `@limiter.limit(...)` on each sensitive endpoint.
3. A stacked **per-session** `@limiter.limit(..., key_func=user_key)` keyed by `sha256(session_cookie)[:16]` so an attacker rotating IPs against a single account still hits a session-scoped bucket. Unauthenticated calls fall back to IP.

- **Local dev (fast path):** leave `RATE_LIMIT_STORAGE_URI=memory://` in `.env`. Buckets live in-process; no Valkey needed. This is only accepted when `ENABLE_DEV_AUTH=true`.
- **Local dev against Valkey (recommended for testing multi-worker setups):**

  ```bash
  RATE_LIMIT_STORAGE_URI="redis://:${VALKEY_PASSWORD}@127.0.0.1:6379/0" make dev-backend
  ```

- **Production:** point at a TLS-protected Valkey with dedicated credentials:

  ```env
  RATE_LIMIT_STORAGE_URI=rediss://app_user:REDACTED@valkey.prod:6380/0?ssl_cert_reqs=required
  RATE_LIMIT_STRATEGY=moving-window
  RATE_LIMIT_FAIL_OPEN=false
  ```

  The backend refuses to boot in a non-dev environment when `RATE_LIMIT_STORAGE_URI=memory://` — an in-process limiter across multiple uvicorn workers silently multiplies an attacker's budget.

`infra/valkey/valkey.conf` ships hardened by default: no on-disk persistence, bounded memory with LRU eviction, `CONFIG`/`FLUSHDB`/`FLUSHALL`/`DEBUG`/`SHUTDOWN` (and similar) renamed to empty strings, and a commented-out TLS + ACL stanza to uncomment once certs are mounted into `/certs`.

### Local API sign-in (development only)

Set `ENABLE_DEV_AUTH=true` for the backend (see `backend/app/core/config.py`). Then use **Sign in (development)** on `/#/login`. The login page auto-hides providers whose OAuth credentials are not configured and shows admin instructions when nothing is available.

### Audit log

Privileged mutations are recorded in an append-only `audit_logs` table (Alembic migration `20260417_0005`). Reads:

- `GET /api/v1/audit-log` — the caller's own actions (self-scoped).
- `GET /api/v1/audit-log?org_slug=…` — entries for an organization (owner-only; non-owners receive 404 to avoid leaking existence).

Extending coverage: call `app.services.audit_service.record(...)` inside the same transaction as the mutation; the service flushes but leaves the commit to the caller.

### Architecture & conventions

See [`docs/plans/exetasi-implementation-plan.md`](docs/plans/exetasi-implementation-plan.md) for the full architecture diagram, phase breakdown, and the **Security & Operations (implemented)** section that documents rate limiting, audit logging, role awareness, OAuth provider gating, and theming as they exist today.

## Quality checks

```bash
pnpm lint
pnpm format
pnpm test
pnpm test:e2e
pnpm build
make test   # frontend + backend tests
```

## Customize Quasar

See [Configuring quasar.config file](https://v2.quasar.dev/quasar-cli-vite/quasar-config-file).
