import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from app import models  # noqa: F401 — registers tables on Base.metadata before create_all()
from app.api.routes import billing, jobs, preview, projects, uploads
from app.api.routes import settings as settings_routes
from app.core.config import get_settings
from app.core.db import Base, engine
from app.core.errors import AppError
from app.core.logging import configure_logging

configure_logging()
app_settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # create_all() is a no-op for tables that already exist — fine for SQLite/MVP.
    # Swap for Alembic migrations when Phase 2 moves to Postgres (docs/implementation_plan.md §2.1).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=app_settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Binds an X-Request-Id (incoming or generated) to every log line for the request's
    duration via loguru's contextvar-based contextualize(), and echoes it back to the
    caller — matches gpu_worker's request_id convention for cross-service log correlation.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        with logger.contextualize(request_id=request_id):
            request.state.request_id = request_id
            response = await call_next(request)
            response.headers["X-Request-Id"] = request_id
            return response


app.add_middleware(RequestIdMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    body = {"error": exc.message, "code": exc.code}
    return JSONResponse(status_code=exc.status_code, content=body)


for router in (
    projects.router,
    uploads.router,
    jobs.router,
    preview.router,
    billing.router,
    settings_routes.router,
):
    app.include_router(router)
