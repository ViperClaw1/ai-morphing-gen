import asyncio
from dataclasses import dataclass

import torch
from PIL import Image
from loguru import logger

from app.core.config import get_settings
from app.core.model_loader import ModelLoadError, get_model_loader
from app.schemas.requests import RepairParams
from app.services.face_embedding import get_face_embedder
from app.services.image_resize import resize_for_inference
from app.services.memory_cleanup import cleanup_after_inference
from app.utils.cuda_utils import get_vram_usage_mb


class CudaOutOfMemoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class RepairResult:
    image: Image.Image
    seed: int
    duration_ms: int
    output_width: int
    output_height: int


def _run_inference_sync(
    image: Image.Image,
    params: RepairParams,
    negative_prompt: str,
) -> RepairResult:
    settings = get_settings()
    loader = get_model_loader()
    pipeline = loader.get_pipeline()

    resized, (out_w, out_h) = resize_for_inference(image)

    face_embeds = get_face_embedder().get_embedding(image).to(
        device=settings.device, dtype=pipeline.unet.dtype
    )

    generator = torch.Generator(device=settings.device).manual_seed(params.seed)

    output = None
    result_image: Image.Image | None = None
    try:
        with torch.inference_mode():
            output = pipeline(
                prompt=params.prompt,
                negative_prompt=negative_prompt,
                image=resized,
                strength=params.strength,
                guidance_scale=params.guidance_scale,
                num_inference_steps=params.num_inference_steps,
                generator=generator,
                ip_adapter_image_embeds=[face_embeds],
            )
            result_image = output.images[0].convert("RGB")
    except torch.cuda.OutOfMemoryError as exc:
        raise CudaOutOfMemoryError("CUDA out of memory during inference.") from exc
    finally:
        if output is not None:
            if hasattr(output, "images"):
                output.images.clear()
            del output
        cleanup_after_inference(resized, generator)

    if result_image is None:
        raise RuntimeError("Inference produced no image.")

    return RepairResult(
        image=result_image,
        seed=params.seed,
        duration_ms=0,
        output_width=out_w,
        output_height=out_h,
    )


async def run_repair(
    image: Image.Image,
    params: RepairParams,
    request_id: str,
) -> RepairResult:
    settings = get_settings()
    negative_prompt = params.negative_prompt or settings.default_negative_prompt

    if not get_model_loader().is_loaded:
        raise ModelLoadError("Pipeline not loaded.")

    log = logger.bind(
        request_id=request_id,
        seed=params.seed,
        guidance_scale=params.guidance_scale,
        num_inference_steps=params.num_inference_steps,
        image_size=f"{image.width}x{image.height}",
    )

    import time

    start = time.perf_counter()
    vram_before = get_vram_usage_mb()

    try:
        result = await asyncio.to_thread(
            _run_inference_sync,
            image,
            params,
            negative_prompt,
        )
    except CudaOutOfMemoryError:
        log.error("CUDA OOM during inference | VRAM: {}", get_vram_usage_mb())
        cleanup_after_inference()
        raise
    except Exception:
        cleanup_after_inference()
        raise

    duration_ms = int((time.perf_counter() - start) * 1000)
    vram_after = get_vram_usage_mb()
    log.info(
        "Inference complete | duration_ms={} | output={}x{} | vram_before={} | vram_after={}",
        duration_ms,
        result.output_width,
        result.output_height,
        vram_before,
        vram_after,
    )

    return RepairResult(
        image=result.image,
        seed=result.seed,
        duration_ms=duration_ms,
        output_width=result.output_width,
        output_height=result.output_height,
    )
