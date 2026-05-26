import time
from contextlib import contextmanager
from typing import Generator


@contextmanager
def measure_ms() -> Generator[list[int], None, None]:
    result: list[int] = [0]
    start = time.perf_counter()
    try:
        yield result
    finally:
        result[0] = int((time.perf_counter() - start) * 1000)
