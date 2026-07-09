# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`eodaego-ai` is the internal-only AI backend for **어대GO**, a mobile app where visitors to Seoul Children's Grand Park follow AI-recommended routes, photograph animals/plants/places, and complete a "collection" (도감) via quizzes. This FastAPI service is never called by the mobile app (Flutter) or by any browser directly — every request comes from `eodaego-server` (Spring Boot, BE) over a private Docker bridge network (`eodaego-internal`), authenticated with a shared `X-Internal-Api-Key` header.

Currently implemented domains: `crawling` (schedule-config CRUD driving APScheduler jobs) and `prompt` (prompt-template CRUD). The `recommendation` domain (LLM-based course recommendation — the app's core feature) is designed (see `docs/superpowers/specs/2026-07-06-ai-service-separation-design.md`) but not yet implemented.

Project rules live in `.claude/rules/*.md` — read those for team conventions, architecture boundaries, testing policy, and delivery/PR process. This file only covers commands and architecture that require reading multiple files to piece together.

## Commands

- Install deps: `uv sync`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Type check (strict): `uv run mypy app`
- Run locally: `APP_ENV=local uv run uvicorn app.main:app --reload --port 8000` (requires `.env.local` with `INTERNAL_API_KEY` and `DATABASE_URL`)
- Create migration: `uv run alembic revision --autogenerate -m "message"` (review the generated file before applying — autogenerate misses index/type details)
- Apply migration: `uv run alembic upgrade head`
- Build image: `docker build -t eodaego-ai .`

No test suite exists — this repo does not write test code (decided 2026-07-09, mirrors `eodaego-server`'s policy). Verify changes via `ruff`/`mypy` and manual checks against `/docs` (Swagger) or `curl`.

## Architecture

**Request flow**: FE(Flutter) → BE(`eodaego-server`, Spring Boot) → this service. The admin UI for managing prompts/schedules is server-rendered inside `eodaego-server`; BE calls this service's CRUD endpoints internally. This service is never reachable from a browser or from FE directly.

**Domain-based layout** (`app/domains/<name>/`): each domain owns `router.py` (HTTP layer only — auth dependency + calls into service, no business logic), `service.py` (business logic + DB access via SQLAlchemy `Session`, no repository abstraction), `model.py` (SQLAlchemy ORM), `schema.py` (Pydantic `*Create`/`*Update`/`*Response` DTOs). Domains do not import each other's model/service directly.

**Auth**: every router except `/health` is registered with `dependencies=[Depends(verify_internal_api_key)]` (`app/core/security.py`), which checks the `X-Internal-Api-Key` header against `Settings.internal_api_key` and 401s on mismatch. This is the second line of defense — the first is that the container never publishes a host port (see Deployment).

**Errors**: raise `fastapi.HTTPException` from routers/services; `app/core/errors.py` registers global handlers that convert `HTTPException`, `RequestValidationError`, and any unhandled `Exception` into one envelope: `{"success": false, "data": null, "error": {"code": ..., "message": ...}}`. Don't hand-build `JSONResponse` error bodies in individual routers.

**Database**: single synchronous SQLAlchemy engine (`psycopg` sync driver) — no async session anywhere, by design, so the engine/session pattern stays identical between FastAPI routers (sync `def`, run in threadpool) and APScheduler jobs. `app/db/session.py` exposes `get_engine()` (lru_cached) and the `get_db()` FastAPI dependency. `app/db/base.py`'s `Base` is what `alembic/env.py` uses as `target_metadata`.

**Scheduler**: `app/scheduler/registry.py` uses APScheduler's `BackgroundScheduler` with the default in-memory jobstore (not `SQLAlchemyJobStore`, to avoid pickling job functions). The `schedule_config` table (owned by the `crawling` domain) is the source of truth for *what* should run; `bootstrap_scheduler()` reads active rows at app startup and calls `scheduler.add_job()` for each. `JOB_REGISTRY` maps `job_id` → callable and is currently empty — the actual crawling jobs (`congestion_job`, `catalog_job`) aren't implemented yet. A schedule config with no matching registry entry is silently skipped; a bad `trigger_config` logs a warning and is skipped rather than crashing startup.

**Deployment**: single Docker container (`eodaego-ai`, internal port 8000), never given a `-p` host-port publish — it only joins the shared bridge network `eodaego-internal`, which is how `eodaego-server` reaches it (by container name). `.github/workflows/python-server-cicd.yml` builds/pushes to DockerHub then SSHes into the NAS to redeploy, creating the `eodaego-internal` network if it doesn't already exist. uvicorn must bind `0.0.0.0` (not `127.0.0.1`) or same-network containers can't reach it.
