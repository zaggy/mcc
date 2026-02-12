# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mission Control Center (MCC) is a multi-agent AI software development platform that orchestrates a virtual software company. It manages specialized AI agents (Architect, Coders, Tester, Code Reviewer) through a structured workflow: GitHub Issue → Architect Planning → Coder Implementation → Tester Validation + Code Review → Merge → CI/CD.

**Status:** Planning phase complete (Phase 1). Implementation not yet started (Phase 2+).

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, FastAPI BackgroundTasks (MVP) / Celery + Redis (production)
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS + shadcn/ui, Zustand, React Query
- **Database:** PostgreSQL 15+ (production), SQLite (MVP/dev)
- **WebSocket:** Socket.io (both server and client)
- **LLM Provider:** OpenRouter API
- **Infrastructure:** Docker + Docker Compose, Caddy/Nginx reverse proxy

## Architecture

Monolithic backend with modular design. Planned directory structure:

```
app/                        # Backend (FastAPI)
├── api/                    # REST + WebSocket route handlers
├── core/                   # Config, security (JWT/2FA), exceptions
├── db/                     # SQLAlchemy models, DB session
├── services/               # Business logic (agents, GitHub, OpenRouter, budget, notifications)
├── agents/                 # Agent implementations (base, architect, coder, tester, reviewer, orchestrator)
├── models/                 # Pydantic request/response models
└── main.py                 # Application entry point

src/                        # Frontend (React SPA)
```

### Agent Types and Communication

Five agent types with defined communication rules:
- **Orchestrator** (user) — can message any agent
- **Architect** — analyzes requirements, creates specs; messages coders/tester/reviewer
- **Coders** (1-2 instances) — implement features in separate branches
- **Tester** — validates against requirements; messages coders for bug reports
- **Code Reviewer** — checks quality/security; messages coders for feedback

Agents use local git worktrees per project (`/data/repos/{project_id}/agent_{id}/`). Orchestrator and Architect have persistent memory; other agents get fresh context per task.

### Key Design Decisions

- JWT auth with 15-min expiry + 7-day refresh tokens, optional TOTP 2FA
- Hierarchical budget limits (global → project → agent → agent_type) with pre-flight checks, 80% soft warning, 100% hard stop, emergency pause
- GitHub Apps API with webhook-driven real-time sync
- Background tasks: FastAPI BackgroundTasks for MVP; Celery queues (`agent_tasks`, `github_sync`, `notifications`, `budget_checks`) for production
- Per-project `.mcc/` directory for agent rule files (AGENTS.md)
- Database schema has 13 tables (see `docs/DB_SCHEMA.md`); use SQLAlchemy's portable types (`Uuid`, `JSON`) — avoid PostgreSQL-specific features (JSONB, gen_random_uuid) in application code for SQLite compatibility

## Workflow

- Always work in a feature branch — never commit directly to `main`.
- Submit all work as pull requests for review before merging.
- Branch naming: use descriptive names like `fix/schema-issues`, `feat/auth-system`, `docs/api-spec-update`.

## Key Documentation

- `PROJECT_PLAN.md` — 8-phase roadmap with detailed task breakdown
- `docs/TECH_SPECS.md` — system architecture, component details, communication flows
- `docs/API_SPEC.md` — REST endpoints, WebSocket events, auth, rate limits
- `docs/DB_SCHEMA.md` — full SQL schema with indexes and relationships

## MVP Scope (Phases 1-4)

Single project, SQLite (no Redis/Celery required), one of each agent type, basic token tracking, simple budget warnings (no hard stops), manual PR merging, email-only notifications.
