# Exetasi — Agent Instructions

Free, open-source quiz and exam web application. Full product specification is in `Requirements.md`.

## Stack

- **Frontend**: Quasar 2 (Vue 3 / TypeScript) SPA; Capacitor for mobile
- **Backend**: FastAPI (Python) — separate project
- **Database**: PostgreSQL
- **State**: Pinia; **Routing**: Vue Router 4 (hash mode); **i18n**: vue-i18n 11
- **Package manager**: pnpm (never npm or yarn)

## Monorepo layout

- **Frontend:** `frontend/` (Quasar); run pnpm commands with `pnpm --dir frontend …` or `cd frontend`
- **Backend:** `backend/` (FastAPI + uv)
- **Postgres:** root `docker-compose.yml`; `Makefile` targets `db-up`, `db-down`, `db-verify`

## Build & Run

From the **repository root** (unless noted):

```bash
pnpm install              # workspace + frontend deps
cd backend && uv sync --extra dev   # Python deps (or: make install)

make db-up                # PostgreSQL (docker compose by default)
make db-up COMPOSE='nerdctl compose'   # same stack via containerd + nerdctl
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

## Domain Model

Entity hierarchy: `User → Organization → Exam → Version → Section → Question → Answer`

- Each user has a personal org auto-created on registration
- Exactly one version per exam is active at a time
- Sections draw a randomised subset from their question pool per attempt
- Question types: multiple choice, open-ended, fill-in-the-blank (`{{n}}`), drag-and-drop ordering, matching, informational
- Manually graded answers surface in the Grading Queue

See `Requirements.md` for complete specification including scoring formulas, roles, analytics, and deployment targets.
