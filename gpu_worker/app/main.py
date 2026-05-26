from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from loguru import logger

from app.api.routes import inference
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.model_loader import ModelLoadError, get_model_loader
from app.utils.cuda_utils import assert_cuda_available, get_device_name


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    settings = get_settings()
    log = logger.bind(component="startup")

    try:
        assert_cuda_available()
        log.info("CUDA device: {}", get_device_name())
    except RuntimeError as exc:
        log.error("CUDA check failed: {}", exc)
        raise

    loader = get_model_loader()
    try:
        loader.load(settings)
    except ModelLoadError as exc:
        log.error("Startup model preload failed: {}", exc)
        raise

    log.info(
        "GPU Worker ready | model={} | load_ms={}",
        settings.model_id,
        loader.load_duration_ms,
    )
    yield
    log.info("GPU Worker shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
    )
    application.include_router(inference.router)
    return application


app = create_app()
