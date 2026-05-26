import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.config import get_settings

T = TypeVar("T")


class InferenceTimeoutError(TimeoutError):
    """Raised when GPU inference exceeds configured timeout."""


async def run_with_timeout(
    coro_factory: Callable[[], Awaitable[T]],
    timeout_seconds: float | None = None,
) -> T:
    settings = get_settings()
    timeout = timeout_seconds if timeout_seconds is not None else settings.inference_timeout_seconds
    try:
        return await asyncio.wait_for(coro_factory(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise InferenceTimeoutError(
            f"Inference exceeded timeout of {timeout} seconds."
        ) from exc
