import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.core.config import get_settings


class InferenceLock:
    """Limits concurrent GPU inference to avoid VRAM corruption."""

    def __init__(self, max_concurrent: int) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        await self._semaphore.acquire()
        try:
            yield
        finally:
            self._semaphore.release()


_inference_lock: InferenceLock | None = None


def get_inference_lock() -> InferenceLock:
    global _inference_lock
    if _inference_lock is None:
        settings = get_settings()
        _inference_lock = InferenceLock(settings.max_concurrent_inference)
    return _inference_lock
