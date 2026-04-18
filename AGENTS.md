# Exetasi — Agent Instructions

Free, open-source quiz and exam web application. Full product specification is in `Requirements.md`.

## Stack

- **Frontend**: Quasar 2 (Vue 3 / TypeScript) SPA; Capacitor for mobile
- **Backend**: FastAPI (Python) — separate project
- **Database**: PostgreSQL (primary store); **Valkey** for shared rate-limit counters
- **State**: Pinia; **Routing**: Vue Router 4 (hash mode); **i18n**: vue-i18n 11
- **Package manager**: pnpm (never npm or yarn)

## Monorepo layout

- **Frontend:** `frontend/` (Quasar); run pnpm commands with `pnpm --dir frontend …` or `cd frontend`
- **Backend:** `backend/` (FastAPI + uv)
- **Infra:** root `docker-compose.yml` (Postgres + Valkey); `infra/valkey/valkey.conf` (hardened); `Makefile` targets `infra-up`/`infra-down`, `db-up`/`db-down`, `valkey-up`/`valkey-down`, `db-verify`
- **Env:** root `.env.example` is the source of truth for environment variables; real `.env` is gitignored

## Build & Run

From the **repository root** (unless noted):

```bash
pnpm install              # workspace + frontend deps
cd backend && uv sync --extra dev   # Python deps (or: make install)

cp .env.example .env      # fill in SESSION_SECRET + VALKEY_PASSWORD
make infra-up             # Postgres + Valkey (docker compose by default)
make infra-up COMPOSE='nerdctl compose'   # same stack via containerd + nerdctl
cd backend && uv run alembic upgrade head

make dev-backend          # FastAPI :8000
make dev-frontend         # Quasar dev server (see frontend/package.json)
```

Frontend-only shortcuts from `frontend/`:

```bash
pnpm dev        # dev server with hot reload
pnpm build      # production build → dist/spa/
pnpm lint       # ESLint check
pnpm format     # Prettier format
```

Root workspace scripts (`pnpm lint`, `pnpm test`, etc.) run the configured workspace packages; see root `package.json`.

## Code Rules

1. **Vue SFCs**: always `<script setup lang="ts">` — no Options API
2. **TypeScript**: strict mode; no `any`; no unchecked `as` casts
3. **Components**: PascalCase filenames; use Quasar components over native HTML
4. **Pinia stores**: setup-syntax `defineStore`; one store per domain concept
5. **i18n**: all user-visible strings via `t('key')` — no hardcoded UI copy
6. **Styles**: Quasar utilities first; SCSS in `frontend/src/css/`; scoped styles in SFCs
7. **Imports**: `#q-app/wrappers` for Quasar config types; auto-imports are active

## Platform conventions (backend)

Load-bearing cross-cutting rules — break these and you weaken the threat model. Full rationale in [`docs/plans/exetasi-implementation-plan.md#security--operations-implemented`](docs/plans/exetasi-implementation-plan.md#security--operations-implemented).

### Rate limiting (slowapi + Valkey)

- Every mutating or auth-related endpoint **must** stack two limits:

  ```python
  from fastapi import Request
  from app.core.ratelimit import limiter, user_key

  @router.post("/resource")
  @limiter.limit("20/minute")                       # per-IP
  @limiter.limit("40/minute", key_func=user_key)    # per-session (IP fallback)
  async def create_resource(request: Request, ...):
      ...
  ```

- The handler **must accept `request: Request`** — slowapi inspects the signature to find it.
- Use `ip_key` / `user_key` from `app.core.ratelimit`; do not invent new key functions without reviewing trusted-proxy handling.
- A global `default_limits=["600/minute"]` is already applied by `SlowAPIMiddleware`. Don't rely on it as the only limit on a sensitive endpoint.
- In production `RATE_LIMIT_STORAGE_URI` must point at Valkey (`redis://` / `rediss://`); `memory://` is rejected by `get_settings()` unless `ENABLE_DEV_AUTH=true`.

### Audit logging

- Privileged mutations go through `app.services.audit_service.record(...)`:

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
  await db.commit()  # caller commits so the audit row shares the mutation's tx
  ```

- `audit_service.record` flushes but never commits. If the surrounding transaction rolls back, the audit row rolls back with it — no ghost rows.
- Action strings are dotted, lowercase, and stable (e.g. `auth.login.oauth.github`, `user.updated`, `org.created`). Reuse existing namespaces before inventing new ones.

### Role awareness

- Membership roles are `Literal["owner", "editor", "grader", "viewer"]` (`MembershipRole` in `app/models/organization.py`). Do not widen this tuple without migrating the DB.
- Enforce role checks at the **service layer**, not only in route handlers. Prefer returning 404 over 403 for reads that would otherwise leak existence (see `GET /audit-log` org-scope).

### OAuth provider gating

- `GET /api/v1/auth/providers` is the single source of truth for which providers are offered; the login page renders buttons from this response. When adding a provider, update both the endpoint and the gating helper.
- OAuth-supplied usernames **must** pass through `app.utils.username.sanitize_oauth_username` before being persisted.
- On state-cookie validation failure, use `_login_error_redirect(...)` — never surface a raw 400 to the user.

### Super-users, bans, and org creation gating

- The `User` model carries four platform-level flags: `is_superuser`, `can_create_orgs`, `is_banned`, `ban_reason`.
- **First-user bootstrap**: the first successful login (any provider, dev login included) flips `is_superuser=True` automatically. See `auth._promote_if_first_user(...)`.
- **Banned login**: `get_current_user` raises `403 {code: "banned", reason}` when the session owner is banned; OAuth callbacks and dev login short-circuit with a redirect carrying `?error=banned`. The client clears its cookies in that case.
- **Org creation**: `POST /api/v1/orgs` now denies anyone whose `is_superuser` and `can_create_orgs` are both `False`. No UI exposes the button to users who lack the permission.
- **Admin surface**: `/api/v1/admin/*` routes require `get_current_superuser`. Unauthorized callers get `404 Not Found`, never `403` — this keeps the very existence of the endpoints hidden. The SPA mirrors the behaviour by redirecting non-superusers away from `/#/admin`.
- Every mutation under `admin_service.*` writes an `AuditLog` row before the caller commits (`audit_service.record` flushes, the handler commits).

### Messaging

- `Message(sender_id, recipient_id, target_kind, target_org_id, body, read_at)` is a flat envelope row. Fan-outs (to **org owners** and **super-users**) create one row per recipient so the inbox queries stay trivial.
- Send endpoints: `POST /api/v1/messages/to-user/{username}`, `POST /api/v1/messages/to-org/{slug}`, `POST /api/v1/messages/to-superusers`.
- Anti-enumeration: unknown/banned direct recipients return `404` identically to "user doesn't exist"; unknown orgs do the same. `message_service.send_to_user` rate-limits the "not found" path.
- Anti-duplicate: a 30-second de-dup window prevents the same `(sender, recipient, body, target_kind)` tuple from stacking multiple rows in a row (e.g. double-clicks or retries).
- Body is server-validated to ≤ 500 UTF-8 characters. Empty/whitespace-only bodies return `422`.

### Alerts and announcements

- `SystemAnnouncement` (global) and `OrgAlert` (per-org) both carry `title`, `body`, severity (`info|warning|critical`), optional `starts_at`/`ends_at`, and `dismissible`.
- The "active" lists (`GET /announcements/active`, `GET /orgs/{slug}/alerts/active`) filter by window (`starts_at ≤ now ≤ ends_at`, either endpoint may be null) **and** strip rows the caller already acknowledged (see `AlertAcknowledgement`).
- System announcements are authored by super-users; org alerts by org owners or super-users. Admin / org-settings CRUD screens list `all` (including scheduled/expired) so authors can manage them.
- The client shows alerts in a `AlertDialog.vue` modal and calls `POST /alerts/{kind}/{alert_id}/ack` when the user dismisses one. Non-dismissible alerts render "Got it" instead of "Dismiss" and still call ack on close so they don't re-appear.

## Domain Model

Entity hierarchy: `User → Organization → Exam → Version → Section → Question → Answer`

- Each user has a personal org auto-created on registration
- Exactly one version per exam is active at a time
- Sections draw a randomised subset from their question pool per attempt
- Question types: multiple choice, open-ended, fill-in-the-blank (`{{n}}`), drag-and-drop ordering, matching, informational
- Manually graded answers surface in the Grading Queue

See `Requirements.md` for complete specification including scoring formulas, roles, analytics, and deployment targets.

## Cursor Cloud specific instructions

### Services overview

| Service         | Port | Start command                                                                                         |
| --------------- | ---- | ----------------------------------------------------------------------------------------------------- |
| PostgreSQL 16   | 5432 | `sudo pg_ctlcluster 16 main start` (installed via apt; Docker pull is blocked by egress restrictions) |
| FastAPI backend | 8000 | `ENABLE_DEV_AUTH=true make dev-backend`                                                               |
| Quasar frontend | 9000 | `make dev-frontend`                                                                                   |

### PostgreSQL

Docker image pulls are blocked by network egress restrictions in Cloud Agent VMs. PostgreSQL 16 is installed directly via `apt` instead of Docker Compose. The database, user, and password all use `exetasi` (matching `docker-compose.yml` defaults). Before starting the backend, ensure PostgreSQL is running:

```bash
sudo pg_ctlcluster 16 main start
```

If the `exetasi` database/user doesn't exist yet (first run only):

```bash
sudo -u postgres psql -c "CREATE USER exetasi WITH PASSWORD 'exetasi';"
sudo -u postgres psql -c "CREATE DATABASE exetasi OWNER exetasi;"
```

Then run migrations: `cd backend && uv run alembic upgrade head`

### Dev authentication

Set `ENABLE_DEV_AUTH=true` when starting the backend to enable the development-only login endpoint. The login page at `/#/login` will show a "Sign in (development)" form where you can enter any username — it auto-creates users. Other OAuth buttons only appear when the matching `{GOOGLE,GITHUB,GITLAB}_CLIENT_ID`/`_SECRET` pairs are populated.

### Rate limiting in the Cloud Agent VM

Valkey is not available (egress restrictions). Leave `RATE_LIMIT_STORAGE_URI=memory://` (the default) and keep `ENABLE_DEV_AUTH=true` so `get_settings()` accepts it. The production guard (`RuntimeError` on `memory://` outside dev mode) is deliberate — don't disable it.

### Quality checks

Standard commands from the repo root (see `Build & Run` section above and root `package.json`):

- `pnpm lint` — ESLint
- `pnpm test` — frontend Vitest
- `cd backend && uv run pytest` — backend tests (uses aiosqlite, no Postgres needed)
- `pnpm build` — production SPA build

### Caveats

- The backend tests use aiosqlite (in-memory), so they run without a PostgreSQL instance.
- The frontend dev server proxies `/api` to `http://127.0.0.1:8000`; both servers must be running for full-stack testing.
- `uv` is installed via `pip install uv` (the `astral.sh` install script is blocked by egress restrictions).
