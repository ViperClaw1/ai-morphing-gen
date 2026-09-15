import base64
import io

import httpx
from loguru import logger
from PIL import Image

from app.core.config import get_settings


class GpuRepairError(RuntimeError):
    """Raised for any non-2xx or `{"success": false}` response from gpu_worker's /repair.
    Carries the same code/message shape gpu_worker itself uses, so callers can branch on
    `.code` (e.g. "CUDA_OOM", "INFERENCE_TIMEOUT") the same way its own tests do.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def repair_frame(
    image: Image.Image,
    *,
    prompt: str,
    seed: int,
    negative_prompt: str | None = None,
    strength: float = 0.2,
    guidance_scale: float = 5.0,
    num_inference_steps: int = 25,
    request_id: str | None = None,
) -> Image.Image:
    """Calls gpu_worker's POST /repair with one frame, returns the repaired image.

    One HTTP call per frame — no batching, no async fan-out. gpu_worker enforces
    max_concurrent_inference=1 server-side regardless, so parallel calls from here would
    just queue up behind its own semaphore while holding open connections for no benefit.
    """
    settings = get_settings()
    if not settings.runpod_endpoint_url:
        raise GpuRepairError("NO_ENDPOINT_CONFIGURED", "RUNPOD_ENDPOINT_URL is not set.")

    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    buf.seek(0)

    data = {
        "prompt": prompt,
        "seed": str(seed),
        "strength": str(strength),
        "guidance_scale": str(guidance_scale),
        "num_inference_steps": str(num_inference_steps),
    }
    if negative_prompt:
        data["negative_prompt"] = negative_prompt

    headers = {}
    if settings.runpod_api_key:
        headers["Authorization"] = f"Bearer {settings.runpod_api_key}"
    if request_id:
        headers["X-Request-Id"] = request_id

    url = f"{settings.runpod_endpoint_url.rstrip('/')}/repair"
    log = logger.bind(request_id=request_id, seed=seed)

    try:
        # Timeout comfortably above gpu_worker's own INFERENCE_TIMEOUT_SECONDS (120s
        # default) so the server's own timeout response wins the race, not this client.
        response = httpx.post(
            url,
            files={"image": ("frame.png", buf, "image/png")},
            data=data,
            headers=headers,
            timeout=180.0,
        )
    except httpx.RequestError as exc:
        log.error("gpu_worker unreachable at {}: {}", url, exc)
        raise GpuRepairError("GPU_UNREACHABLE", f"Could not reach gpu_worker: {exc}") from exc

    try:
        body = response.json()
    except ValueError as exc:
        raise GpuRepairError("INVALID_RESPONSE", "gpu_worker returned non-JSON body.") from exc

    if not body.get("success"):
        error = body.get("error", {})
        raise GpuRepairError(
            error.get("code", "UNKNOWN"),
            error.get("message", f"HTTP {response.status_code}"),
        )

    image_b64 = body["data"]["image_base64"]
    return Image.open(io.BytesIO(base64.b64decode(image_b64)))
