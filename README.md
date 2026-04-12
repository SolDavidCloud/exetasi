# exetasi (exetasi)

Free quiz and exam webapp (monorepo: Quasar frontend + FastAPI backend).

Implementation plan: [docs/plans/exetasi-implementation-plan.md](docs/plans/exetasi-implementation-plan.md).

## Prerequisites

- [Node.js](https://nodejs.org/) 22+ and [pnpm](https://pnpm.io/) 10+
- [uv](https://docs.astral.sh/uv/) (Python 3.12+)
- **PostgreSQL via Compose** — either:
  - [Docker](https://docs.docker.com/get-docker/) with Compose (`docker compose`), or
  - [containerd](https://containerd.io/) + [nerdctl](https://github.com/containerd/nerdctl) with the Compose subcommand (`nerdctl compose`; needs CNI for published ports)

Check your Compose CLI: `make db-verify` (Docker) or `make db-verify COMPOSE='nerdctl compose'` (nerdctl).

## Install

From the repository root:

```bash
pnpm install
cd backend && uv sync --extra dev
```

## Database (local)

**Docker (default):** the Makefile uses `docker compose` unless you override `COMPOSE`.

```bash
make db-up
cd backend && uv run alembic upgrade head
```

**containerd + nerdctl:** same `docker-compose.yml`, pass Compose explicitly (quote the value so Make treats it as one assignment):

```bash
make db-up COMPOSE='nerdctl compose'
make db-down COMPOSE='nerdctl compose'   # stop and remove containers/network
make db-verify COMPOSE='nerdctl compose'  # optional: show compose version
```

Credentials and port match `docker-compose.yml`: user, password, and database **`exetasi`**, host **`127.0.0.1`**, port **`5432`**.

## Develop

Run **PostgreSQL** (`make db-up` or `make db-up COMPOSE='nerdctl compose'`), apply migrations, then start **backend** and **frontend** in two terminals:

```bash
make dev-backend
```

```bash
make dev-frontend
```

The Quasar dev server proxies `/api` to `http://127.0.0.1:8000` so the SPA and API share one origin in development (cookies work as first-party).

### Local API sign-in (development only)

Set `ENABLE_DEV_AUTH=true` for the backend (see `backend/app/core/config.py`). Then use **Sign in (development)** on `/#/login`.

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
