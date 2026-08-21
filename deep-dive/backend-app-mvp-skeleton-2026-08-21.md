# Deep Dive: `backend/app/` — FastAPI MVP Skeleton

**Generated**: 2026-08-21
**Files**: `main.py`, `core/config.py`, `core/queue.py`, `core/db.py`, `core/errors.py` (deep), plus 16 supporting files (summarized below)

---

## Overview

This is the scaffolding commit for the backend: a FastAPI app wired up with routers, middleware, config, and a database/queue foundation — but almost every route body just raises a typed `501 Not Implemented`. Nothing does real work yet (no DB writes, no queueing, no R2 calls). The interesting content here isn't business logic, it's the *contract-first* pattern: schemas, error shapes, and queue topology are all locked in per `.claude/rules/api-conventions.md` before any endpoint gets a real implementation. That's a deliberate sequencing choice — it lets the API surface (and its tests) get reviewed independently of the GPU/payment logic that will fill it in later.

---

## Key Components

- `main.py` — assembles the `FastAPI()` app: CORS, a request-ID middleware, a global `AppError` → JSON handler, and router registration.
- `core/config.py` — `Settings(BaseSettings)` pulls all config from `.env`; `get_settings()` is `@lru_cache`'d so it's read once per process.
- `core/queue.py` — creates two RQ `Queue` objects (`preview_gpu`, `full_gpu`) bound to Redis; no in-code priority mechanism, ordering comes from worker startup args.
- `core/db.py` — SQLAlchemy `engine` + `SessionLocal` + `Base`, with a `get_db()` generator for FastAPI's dependency injection.
- `core/errors.py` — `AppError` exception carrying `status_code`/`code`/`message`, the single source of truth for the mandated `{error, code}` response shape.

**Remaining 16 files** (one-liner each):
- `core/stubs.py` — `not_implemented(phase)` helper; raises `AppError(501, ...)` pointing at the implementation-plan section that owns the real logic.
- `core/storage.py` — builds a boto3 `s3` client pointed at Cloudflare R2 (S3-compatible API, no separate SDK).
- `core/logging.py` — configures loguru with a `request_id`/`job_id`-tagged log format, mirroring the GPU worker's log convention.
- `api/routes/projects.py` — `POST/GET/PATCH /projects` — all stubbed.
- `api/routes/uploads.py` — `POST /projects/{id}/assets` — stubbed; comment flags that NSFW/face-detection/size gates belong here later, not before.
- `api/routes/preview.py` — `POST /projects/{id}/preview` and `/render` — both stubbed.
- `api/routes/jobs.py` — `GET /jobs/{id}` — stubbed.
- `api/routes/billing.py` — `POST /checkout` and `/payments/webhook` — stubbed; webhook comment reiterates signature-then-idempotency ordering ahead of implementation.
- `api/routes/settings.py` — `GET /settings/public` — the **only** fully implemented route; just echoes preview config, no DB/queue dependency.
- `schemas/common.py` — `ErrorResponse{error, code}`.
- `schemas/jobs.py` — `JobResponse{job_id, queue_name, state}`, the base every job-related response extends.
- `schemas/preview.py` — `PreviewRequest`, `PreviewJobResponse(JobResponse)`, `RenderRequest`, `RenderJobResponse(JobResponse)`.
- `schemas/projects.py` — `ProjectCreate{title}`, `ProjectResponse{id, title, status}`.
- `schemas/uploads.py` — `AssetResponse{id, project_id, filename, order}`.
- `schemas/billing.py` — `CheckoutRequest{project_id}`, `CheckoutResponse{checkout_url}`.
- `schemas/settings.py` — `PublicSettingsResponse{preview_enabled, preview_limit_per_project, preview_ttl_hours}`.
- `models/__init__.py` — empty; a placeholder comment marks where ORM models attach to `Base`.

> More than 5 files were in scope for this component — the above list covers everything; ask if you'd like a full walkthrough of any specific file (e.g. `core/storage.py` or the route/schema pairs).

---

## Concepts & Decisions

### Settings-as-singleton via `@lru_cache`
- **What**: `get_settings()` wraps a fresh `Settings()` construction in `functools.lru_cache`, so the first call parses `.env` and every later call (across the whole app) returns the same cached instance.
- **Why used here**: FastAPI's own docs recommend this exact pattern — it avoids re-reading and re-validating environment variables on every request while still keeping config injectable/overridable in tests (you can call `get_settings.cache_clear()`).

### RQ priority via queue draining order, not a priority field
- **What**: `core/queue.py` defines `preview_queue` and `full_queue` as two independent RQ `Queue` objects. There's no numeric priority attached to a job.
- **Why used here**: RQ workers drain queues in the order passed on the command line (`rq worker preview_gpu full_gpu`), so "preview always wins" (a hard architecture rule) is enforced by *always listing `preview_gpu` first* wherever a worker is started — not by any code in this file. That's a footgun worth knowing: the guarantee lives in ops/deployment convention, not in a type-checked place.

### Typed exception → fixed error shape
- **What**: `AppError` is a plain exception with `status_code`/`code`/`message`; `main.py` registers a `@app.exception_handler(AppError)` that turns it into `{"error": ..., "code": ...}`.
- **Why used here**: `api-conventions.md` mandates one consistent error shape for every response, and explicitly forbids leaking raw stack traces or FastAPI's default `{"detail": ...}` shape. Centralizing the translation in one handler means every route can just `raise AppError(...)` without repeating JSON-shaping logic.

### "Fail loud" stubs instead of fake success
- **What**: `not_implemented()` raises `AppError(501, "NOT_IMPLEMENTED", ...)` rather than the route returning a hardcoded 200 with dummy data.
- **Why used here**: A stub that returns fake `200` data would let a client (or an integration test) silently pass against an endpoint that does nothing — a 501 forces callers to notice the gap. It also means the Pydantic `response_model` on each route is still exercised for schema review/codegen even though the handler body is empty.

### Request correlation via loguru `contextualize()`
- **What**: `RequestIdMiddleware` in `main.py` binds an `X-Request-Id` (incoming or freshly generated) into a `logger.contextualize(request_id=...)` block for the duration of the request, and `core/logging.py`'s format string prints `request_id=...` on every line.
- **Why used here**: This is a contextvar-based approach — no need to thread `request_id` as an explicit parameter through every function call. It's stated to mirror the GPU worker's convention, so a `request_id`/`job_id` can be grepped across both services' logs for one user-facing operation.

### SQLite session lifecycle for FastAPI's threadpool
- **What**: `engine = create_engine(..., connect_args={"check_same_thread": False})`, paired with a `get_db()` generator dependency that always closes the session in a `finally` block.
- **Why used here**: FastAPI runs sync path operations in a thread pool, so the thread that opens a SQLite connection isn't guaranteed to be the thread that uses it — SQLite's default same-thread check would otherwise raise. This is a SQLite-specific concession; it goes away when Phase 2 migrates to Postgres (`postgres_url` already sits unused in `config.py` for that cutover).

*(`async/await` and REST-API conventions are used throughout but not explained here per your known-concepts list.)*

---

*Generated by AntiVibe · `/antivibe full` for the extended version with resources and line-by-line walkthrough.*
