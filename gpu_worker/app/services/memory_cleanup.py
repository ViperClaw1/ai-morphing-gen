import gc
from typing import Any

import torch


def cleanup_after_inference(*objects: Any) -> None:
    for obj in objects:
        del obj
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
