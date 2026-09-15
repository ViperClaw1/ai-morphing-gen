import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, Header, UploadFile
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError

from app.core.concurrency import get_inference_lock
from app.core.model_loader import ModelLoadError
from app.schemas.requests import RepairParams
from app.schemas.responses import ErrorDetail, ErrorResponse, RepairData, SuccessResponse
from app.services.face_embedding import FaceNotDetectedError
from app.services.image_io import image_to_png_base64
from app.services.repair_pipeline import CudaOutOfMemoryError, run_repair
from app.services.timeout_handler import InferenceTimeoutError, run_with_timeout
from app.utils.image_validation import ImageValidationError, decode_and_validate_image, validate_mime_type

router = APIRouter(tags=["inference"])


def _request_id(x_request_id: str | None) -> str:
    return x_request_id or str(uuid.uuid4())


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


@router.get("/health/live")
async def health_live() -> dict[str, bool]:
    return {"success": True}


@router.post("/repair")
async def repair_frame(
    image: Annotated[UploadFile, File(...)],
    prompt: Annotated[str, Form(...)],
    seed: Annotated[int, Form(...)],
    negative_prompt: Annotated[str | None, Form()] = None,
    strength: Annotated[float, Form()] = 0.2,
    guidance_scale: Annotated[float, Form()] = 5.0,
    num_inference_steps: Annotated[int, Form()] = 25,
    x_request_id: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    request_id = _request_id(x_request_id)
    log = logger.bind(request_id=request_id)

    try:
        params = RepairParams(
            prompt=prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            strength=strength,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
        )
    except ValidationError:
        return _error_response(
            422,
            "INVALID_REQUEST",
            "Invalid repair parameters. Check seed, strength, and step values.",
        )

    try:
        raw_bytes = await image.read()
        mime_type = validate_mime_type(image.content_type)
        validated = decode_and_validate_image(raw_bytes, mime_type)
    except ImageValidationError as exc:
        log.warning("Image validation failed: {} | code={}", exc.message, exc.code)
        status = 413 if exc.code == "INVALID_IMAGE" and "exceeds" in exc.message.lower() else 400
        if exc.code == "UNSUPPORTED_RESOLUTION":
            status = 400
        return _error_response(status, exc.code, exc.message)

    lock = get_inference_lock()
    try:
        async with lock.acquire():
            async def _execute():
                return await run_repair(validated.image, params, request_id)

            result = await run_with_timeout(_execute)
    except FaceNotDetectedError as exc:
        log.warning("No face detected | request_id={}", request_id)
        return _error_response(422, "NO_FACE_DETECTED", str(exc))
    except InferenceTimeoutError as exc:
        log.error("Inference timeout | request_id={}", request_id)
        return _error_response(504, "INFERENCE_TIMEOUT", str(exc))
    except CudaOutOfMemoryError:
        log.error("CUDA OOM | request_id={}", request_id)
        return _error_response(
            503,
            "CUDA_OOM",
            "GPU ran out of memory. Reduce resolution or retry later.",
        )
    except ModelLoadError as exc:
        log.error("Model not loaded: {}", exc)
        return _error_response(
            503,
            "MODEL_LOAD_FAILURE",
            "Inference model is not available.",
        )
    except Exception:
        log.exception("Unexpected inference failure")
        return _error_response(
            500,
            "INFERENCE_FAILED",
            "Inference failed. Check server logs for details.",
        )

    image_b64 = image_to_png_base64(result.image)
    response = SuccessResponse(
        data=RepairData(
            image_base64=image_b64,
            seed=result.seed,
            duration_ms=result.duration_ms,
            mime_type="image/png",
        )
    )
    return JSONResponse(status_code=200, content=response.model_dump())
