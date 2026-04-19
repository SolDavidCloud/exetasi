# Exetasi — Claude Project Context

Free, open-source quiz and exam web application. See `Requirements.md` for the full product specification.

## Stack

| Layer | Technology |
| ----- | ------------ |
| Frontend | Quasar 2 (Vue 3 / TypeScript), SPA + Capacitor mobile wrapper |
| Backend | FastAPI (Python) — separate project/repo |
| Database | PostgreSQL (primary store) |
| Rate-limit store | Valkey (Redis-compatible), hardened `infra/valkey/valkey.conf` |
| State | Pinia (setup-syntax stores) |
| Routing | Vue Router 4 (hash mode) |
| i18n | vue-i18n 11 — all UI strings via translation keys, never hardcoded |
| Package manager | **pnpm** — never use npm or yarn |

## Commands

**Monorepo (repository root):**

```bash
pnpm install
make install            # pnpm + backend uv sync

cp .env.example .env    # fill in SESSION_SECRET + VALKEY_PASSWORD
make infra-up           # PostgreSQL + Valkey: default is `docker compose`
make infra-up COMPOSE='nerdctl compose'   # containerd + nerdctl (quote the assignment)
make infra-down         # optional: same COMPOSE=… when not using Docker
make db-verify          # print `$(COMPOSE) version`

make dev-backend        # uvicorn :8000
make dev-frontend       # Quasar in frontend/
```

**Frontend package** (`frontend/` or `pnpm --dir frontend`):

```bash
pnpm dev        # start dev server (opens browser automatically)
pnpm build      # production SPA build
pnpm lint       # ESLint (flat config)
pnpm format     # Prettier
```

## Project Structure

```text
frontend/
  src/
    assets/       static assets
    boot/         Quasar boot files (run before app mount)
    components/   shared components
    css/          global SCSS; quasar.variables.scss for design tokens
    i18n/         translation files (en-US/index.ts, ...)
    layouts/      page wrapper layouts
    pages/        route-level page components
    router/       Vue Router setup
backend/          FastAPI app (see backend/README.md)
```

## Code Conventions

### Vue

- Always use `<script setup lang="ts">` — no Options API, no `export default defineComponent()`
- Use `defineProps`, `defineEmits`, `defineModel` — no runtime declarations without types
- PascalCase component filenames; Quasar components (`QBtn`, `QCard`, `QInput`) over native HTML equivalents
- Scoped styles in SFCs; global tokens via `quasar.variables.scss`

### TypeScript

- Strict mode is on — no `any`, no unchecked `as` casts
- Prefer `interface` for shapes, `type` for unions/intersections
- Import Quasar config types via `#q-app/wrappers`

### Pinia

- One store per domain concept (e.g., `useAuthStore`, `useExamStore`)
- Use setup-syntax stores (`defineStore('id', () => { ... })`)
- Keep side-effects (API calls) inside actions, not in components

### i18n

- All user-visible strings go through `useI18n().t('key')` — never hardcode UI copy
- Keys are scoped by feature: `exam.title`, `section.description`, etc.

### Styling

- Quasar utility classes preferred over custom CSS where possible
- Custom SCSS lives in `frontend/src/css/`; component-scoped styles for component-specific overrides

## Architecture Notes

- **Monorepo:** Quasar SPA lives under `frontend/`; FastAPI service under `backend/`. They communicate via REST (dev: Quasar proxies `/api` to the backend).
- Router mode is **hash** (`/#/` URLs) for maximum static-hosting compatibility
- Images are stored externally (S3/GCS/R2/local disk) — never commit binary assets beyond `public/icons`
- i18n is structured for future RTL/multi-language support — use string keys from day one
- Two stateful services: **PostgreSQL** (primary data + append-only `audit_logs`) and **Valkey** (shared rate-limit counters). Both ship with `docker-compose.yml`; Valkey is hardened in `infra/valkey/valkey.conf`.

## Platform conventions (backend)

Full rationale in [`docs/plans/exetasi-implementation-plan.md`](docs/plans/exetasi-implementation-plan.md) → **Security & Operations (implemented)**. Cliff notes:

### Rate limiting

- Every mutating or auth endpoint stacks two decorators and accepts `request: Request`:

  ```python
  from fastapi import Request
  from app.core.ratelimit import limiter, user_key

  @router.post("/resource")
  @limiter.limit("20/minute")                      # per-IP
  @limiter.limit("40/minute", key_func=user_key)   # per-session (hashed cookie)
  async def handler(request: Request, ...):
      ...
  ```

- A global `600/minute` per-IP cap is already applied by `SlowAPIMiddleware`.
- Production requires `RATE_LIMIT_STORAGE_URI` pointing at Valkey (`redis://` / `rediss://`); `memory://` is rejected unless `ENABLE_DEV_AUTH=true`.

### Audit logging

- Log privileged mutations via `app.services.audit_service.record(...)` inside the same transaction as the action. The service flushes; the caller commits.
- Use `app.utils.ip.client_ip(request)` for the `ip` field (respects `TRUSTED_PROXY`).
- Action strings are dotted + stable: `auth.login.oauth.{provider}`, `user.updated`, `org.created`, `exam.created`, etc.

### Role awareness

- `MembershipRole = Literal["owner", "editor", "grader", "viewer"]` in `app/models/organization.py`.
- Role checks happen at the service layer. Prefer **404 over 403** on org-scoped reads to avoid leaking existence.

### OAuth

- `GET /api/v1/auth/providers` is the source of truth for which providers render on the login page.
- Sanitise external usernames via `app.utils.username.sanitize_oauth_username` before persisting.
- On OAuth state-cookie failures, use `_login_error_redirect(...)` so the cookie is cleared and the user lands on `/#/login?error=…`.

## Domain Summary

Full specification in `Requirements.md`. Key entity hierarchy:

```text
User → Organization → Exam → Version → Section → Question → Answer
```

- Users have a personal org auto-created on registration; username is globally unique
- Only one exam version is **active** at a time; activating one auto-deactivates the previous
- Sections draw a configurable subset of questions from their pool per attempt
- Six question types: multiple choice, open-ended, fill-in-the-blank (`{{n}}` syntax), drag-and-drop ordering, matching, informational
- Scoring varies per type; see Requirements.md → Scoring for formulas
- Manually graded questions (open-ended, manual fill-in-the-blank) flow through the Grading Queue
