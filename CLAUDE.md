# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mission Control Center (MCC) is a multi-agent AI software development platform that orchestrates a virtual software company. It manages specialized AI agents (Architect, Coders, Tester, Code Reviewer) through a structured workflow: GitHub Issue → Architect Planning → Coder Implementation → Tester Validation + Code Review → Merge → CI/CD.

**Status:** Phase 2 complete. Phase 3 (Agent Core System) next.

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, FastAPI BackgroundTasks (MVP) / Celery + Redis (production)
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS v4 + shadcn/ui, Zustand, React Query
- **Database:** PostgreSQL 15+ (all environments, via Docker Compose for local dev)
- **WebSocket:** Socket.io (both server and client)
- **LLM Provider:** OpenRouter API
- **Infrastructure:** Docker + Docker Compose, Caddy/Nginx reverse proxy
- **Package manager:** `uv` (Python), `npm` (frontend)

## Commands

- **Install deps:** `uv sync --all-extras`
- **Run backend:** `uv run uvicorn app.main:app --reload`
- **Run frontend:** `cd frontend && npm run dev`
- **Lint:** `uv run ruff check app/ tests/`
- **Format:** `uv run ruff format app/ tests/`
- **Test:** `uv run pytest tests/ -v --tb=short`
- **Migrate DB:** `uv run alembic upgrade head`
- **Start Postgres:** `docker compose up postgres -d`
- **Deploy:** `docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build`
- **Rebuild frontend:** `cd frontend && npm run build`

## Architecture

Monolithic backend with modular design:

```
app/                        # Backend (FastAPI)
├── api/                    # REST + WebSocket route handlers
├── core/                   # Config, security (JWT/2FA), exceptions
├── db/                     # SQLAlchemy models, DB session
├── services/               # Business logic
├── agents/                 # Agent implementations
├── models/                 # Pydantic request/response models
└── main.py                 # Application entry point

frontend/                   # Frontend (React SPA)
├── src/
│   ├── components/ui/      # shadcn/ui components
│   ├── pages/              # Route pages
│   └── lib/                # Utilities
```

### Key Design Decisions

- PostgreSQL-only (no SQLite) — use native `UUID`, `JSONB` types
- `pwdlib` with argon2 for password hashing (not passlib)
- `PyJWT` for JWT tokens (not python-jose)
- Tailwind CSS v4 with Vite plugin (no tailwind.config)
- JWT auth with 15-min expiry + 7-day refresh tokens, optional TOTP 2FA
- Hierarchical budget limits with pre-flight checks
- Database schema has 13+ tables (see `docs/DB_SCHEMA.md`)

## Workflow

- Always work in a feature branch — never commit directly to `main`.
- Submit all work as pull requests for review before merging.
- Branch naming: use descriptive names like `fix/schema-issues`, `feat/auth-system`, `docs/api-spec-update`.

## Key Documentation

- `PROJECT_PLAN.md` — 8-phase roadmap with detailed task breakdown
- `docs/TECH_SPECS.md` — system architecture, component details, communication flows
- `docs/API_SPEC.md` — REST endpoints, WebSocket events, auth, rate limits
- `docs/DB_SCHEMA.md` — full SQL schema with indexes and relationships
- `docs/UI_WIREFRAMES.md` — ASCII wireframes for all pages
