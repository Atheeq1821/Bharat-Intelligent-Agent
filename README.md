# Bharat Intelligence Hackathon Project

This repo has:

- `backend/`: FastAPI + LangGraph agent.
- `frontend/`: Next.js chat UI.
- `zoho_books.yaml`: custom Coral source spec.
- `coral/`: Coral setup notes.

## Why Docker Here

Team members should not need to install Coral, Python, or Node locally.

With this setup:

- Coral CLI runs in a container.
- Backend also has Coral CLI available and reads shared Coral state.
- Frontend and backend run with `docker compose up`.

## One-Time Setup

1. Copy env templates:
   - `backend/.env.example` -> `backend/.env`
   - `frontend/.env.example` -> `frontend/.env.local`
2. Fill real credentials in `backend/.env` and `frontend/.env.local`.
3. Build containers:
   - `docker compose build`

## Install Coral Sources (Containerized)

Start Coral container:

```bash
docker compose up -d coral
```

Run guided onboarding inside the container:

```bash
docker compose run --rm coral coral onboard
```

Or run repo helper for Zoho source:

```bash
docker compose run --rm coral setup-coral-sources
```

Optional Slack setup (interactive):

```bash
docker compose run --rm coral coral source add --interactive slack
```

Validate installed sources:

```bash
docker compose run --rm coral coral source list
docker compose run --rm coral coral sql "SELECT schema_name, table_name FROM coral.tables ORDER BY 1,2"
```

## Run Full Stack

```bash
docker compose up
```

App URLs:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`

## Docker Base Image Note

Coral `0.4.x` Linux binary currently requires `GLIBC_2.39+`.
For that reason, this repo uses:

- `python:3.12-slim-trixie` (backend)
- `debian:trixie-slim` (coral utility image)

If you switch back to bookworm-based images, you may hit:
`/lib/x86_64-linux-gnu/libc.so.6: version 'GLIBC_2.39' not found`.

## Supabase Migrations

Run this from repo root:

```bash
python .\run_migrations.py
```

Then execute SQL in Supabase SQL editor:

1. `migrations/001_schema.sql`
2. `migrations/002_seed_data.sql`

## Important Compatibility Note

This project originally referenced a Coral `postgresql` bundled source in agent prompts.
Current Coral `0.4.x` bundled sources do not include `postgresql`, so `postgresql.*`
queries are legacy until a PostgreSQL source spec is added.

Zoho source is validated with:

```bash
coral source lint .\zoho_books.yaml
```

## Local (Non-Docker) Option

If you still want local runtime, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

Then run backend/frontend normally.
