import sys

from loguru import logger

from app.core.config import get_settings


def configure_logging() -> None:
    """Mirrors gpu_worker's loguru setup so both services share one log format/paradigm.
    request_id/job_id are bound per-request/per-job via logger.contextualize() (see
    RequestIdMiddleware in app/main.py) rather than passed explicitly at every call site.
    """
    settings = get_settings()
    logger.remove()
    logger.configure(extra={"request_id": "-", "job_id": "-"})
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level} | "
            "request_id={extra[request_id]} job_id={extra[job_id]} | {name}: {message}"
        ),
    )
