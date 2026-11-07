# Billbo

💸 Self-hosted expense manager: track spending by group and tag. FastAPI + React + PostgreSQL, 🐳 Docker-ready.

![Billbo showing a group's total spent and its expenses by month](docs/images/web_group_expense.png)

## Why

Most expense apps keep your financial data on someone else's servers, lock useful
features behind subscriptions, or are too heavy for simple tracking. I built this
to have a small expense manager that I fully own, it runs on my own machine, and organizes spending
the way I think about it, by group and tag.

## Layout

```text
backend/   FastAPI, SQLAlchemy, PostgreSQL, Alembic
web/       React + Vite + TypeScript, Material UI
```

Features: sign up / log in, expense groups, tags, notes, an expense list with
infinite scroll, and a profile page. The web app is an installable PWA (app
shell cached; data needs the network). A native mobile client is not started.

## Backend

Run from `backend/`.

```bash
cd backend
uv sync
cp .env.example .env   # then fill in DATABASE_URL; never commit .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Environment variables (see [`backend/.env.example`](backend/.env.example)):
`DATABASE_URL`, `CORS_ORIGINS`, `ALLOW_SIGNUP`, `COOKIE_SECURE`, and `BACKEND_PORT` (docker compose only).
The API is served under `/api/v1`, with interactive docs at `/docs` and a
health check at `/health`.

Lint and format check:

```bash
uv run ruff check .
uv run ruff format --check .
```

Create a migration after changing models:

```bash
uv run alembic revision --autogenerate -m "describe change"
```

## Web

Run from `web/`.

```bash
cd web
cp .env.example .env   # VITE_API_URL points at the API
pnpm install
pnpm dev
```

Open the Vite URL shown in the terminal.

```bash
pnpm lint
pnpm build   # type-checks, then builds
pnpm preview # serve the build; the PWA service worker only runs here, not in dev
pnpm test
```

The UI is built with Material UI; the theme lives in `web/src/theme.ts`.

## Docker

Each service has a production `Dockerfile` and its own `compose.yaml`; the root
`docker-compose.yml` includes both. Create `backend/.env` and `web/.env` from
their `.env.example` files first, then:

```bash
docker compose up --build
```

The API is on `BACKEND_PORT` (default 9000 in the example) and the web app on
`WEB_PORT` (9001). The backend container runs `alembic upgrade head` on start,
so no manual migration is needed. Keep `CORS_ORIGINS` set to the web URL.

`VITE_API_URL` is baked into the web bundle at build time, so rebuild after
changing it. PostgreSQL is not part of the compose stack; point `DATABASE_URL`
at an existing instance.

## Pre-commit

`.pre-commit-config.yaml` runs backend Ruff and web lint/build checks.
