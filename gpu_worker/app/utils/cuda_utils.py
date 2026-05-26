import torch


def assert_cuda_available() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is required. CPU inference fallback is forbidden."
        )
    device_count = torch.cuda.device_count()
    if device_count < 1:
        raise RuntimeError("No CUDA devices detected.")


def get_device_name() -> str:
    assert_cuda_available()
    return torch.cuda.get_device_name(0)


def get_vram_usage_mb() -> dict[str, float | None]:
    if not torch.cuda.is_available():
        return {"used_mb": None, "total_mb": None, "free_mb": None}
    try:
        used = torch.cuda.memory_allocated() / (1024**2)
        reserved = torch.cuda.memory_reserved() / (1024**2)
        total = torch.cuda.get_device_properties(0).total_memory / (1024**2)
        return {
            "used_mb": round(used, 2),
            "reserved_mb": round(reserved, 2),
            "total_mb": round(total, 2),
            "free_mb": round(total - reserved, 2),
        }
    except Exception:
        return {"used_mb": None, "total_mb": None, "free_mb": None}
