# AI Morphing Generator — Backend (Phase 1.1 skeleton)

FastAPI + RQ backend. This is the §1.1 Infrastructure Setup slice from
[`docs/implementation_plan.md`](../docs/implementation_plan.md): app skeleton, router
structure, SQLite engine, RQ queue wiring, R2 storage client, and env config.

Business logic is **not** implemented yet. Every route except `GET /settings/public`
returns `501 {"error": ..., "code": "NOT_IMPLEMENTED"}` with a pointer to the plan section
that implements it — see the router files under `app/api/routes/`.

## Layout

```
backend/
├── app/
│   ├── main.py              # app assembly, CORS, request-id middleware, error handler
│   ├── api/routes/          # projects, uploads, jobs, preview, billing, settings
│   ├── core/                # config, db (SQLite), queue (RQ), storage (R2), logging, errors
│   ├── schemas/             # Pydantic request/response models
│   └── models/              # ORM models — empty until §1.3
├── tests/api/
├── requirements.txt
├── pytest.ini
└── .env.example
```

## Local setup

```bash
cd backend
python3.10 -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Redis is only required once RQ jobs are actually enqueued (§1.4+) — the skeleton boots
and `/settings/public` works without it.

## Deploying to Railway

`Dockerfile` builds the app; `railway.toml` points Railway at it and healthchecks
`/settings/public` (the only route with no DB/Redis dependency). One image, two Railway
services:

- **web** — uses the Dockerfile's default `CMD` as-is.
- **worker** — same repo/image, but override its Start Command in the Railway service
  settings to `rq worker preview_gpu full_gpu --url $REDIS_URL` (the `rq` CLI reads
  `RQ_REDIS_URL`, not `REDIS_URL`, so this must be passed explicitly via `--url`).

Both services need: Railway Redis add-on attached (provides `REDIS_URL`), a volume
mounted (e.g. `/data`) with `SQLITE_PATH=/data/app.db` and `STORAGE_PATH=/data/storage`
so the DB and any transient files survive redeploys, plus `RUNPOD_API_KEY`,
`RUNPOD_ENDPOINT_ID`, the R2 credentials, and `CORS_ALLOWED_ORIGINS` set to the deployed
frontend URL — see `app/core/config.py` for the full list.

## Tests

```bash
pytest tests/ -v
```

## Conventions this skeleton establishes

- **Error shape**: every error response is `{"error": str, "code": str}` — enforced by
  the `AppError` exception + handler in `main.py`, not FastAPI's default `{"detail": ...}`.
- **Logging**: `loguru`, matching `gpu_worker`. `request_id` is bound per-request via
  `RequestIdMiddleware`; `job_id` gets bound the same way once RQ workers land (§1.4).
- **Queue priority**: `preview_gpu` before `full_gpu` is enforced by *listing order*
  wherever a worker is started (`rq worker preview_gpu full_gpu`) — RQ has no priority
  field, so this ordering must be preserved everywhere a worker command is written.
