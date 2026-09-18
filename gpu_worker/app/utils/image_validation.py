from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

from app.core.config import get_settings

ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


@dataclass(frozen=True)
class ValidatedImage:
    image: Image.Image
    width: int
    height: int
    mime_type: str


class ImageValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def validate_upload_size(data: bytes) -> None:
    settings = get_settings()
    if len(data) > settings.max_upload_bytes:
        raise ImageValidationError(
            "INVALID_IMAGE",
            f"Upload exceeds maximum size of {settings.max_upload_bytes} bytes.",
        )
    if len(data) == 0:
        raise ImageValidationError("INVALID_IMAGE", "Empty upload.")


def validate_mime_type(content_type: str | None) -> str:
    if not content_type:
        raise ImageValidationError(
            "INVALID_IMAGE",
            "Content-Type header is required.",
        )
    mime = content_type.split(";")[0].strip().lower()
    if mime not in ALLOWED_MIME_TYPES:
        raise ImageValidationError(
            "INVALID_IMAGE",
            f"Unsupported MIME type '{mime}'. Allowed: jpeg, png, webp.",
        )
    return mime


def decode_and_validate_image(data: bytes, mime_type: str) -> ValidatedImage:
    validate_upload_size(data)

    try:
        pil_image = Image.open(BytesIO(data))
        pil_image.load()
    except Exception as exc:
        raise ImageValidationError(
            "CORRUPTED_FILE",
            "Unable to decode image. File may be corrupted.",
        ) from exc

    if pil_image.format is None:
        raise ImageValidationError(
            "CORRUPTED_FILE",
            "Image format could not be determined.",
        )

    # OpenCV decode check for corruption
    np_buffer = np.frombuffer(data, dtype=np.uint8)
    cv_image = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
    if cv_image is None:
        raise ImageValidationError(
            "CORRUPTED_FILE",
            "OpenCV failed to decode image bytes.",
        )

    rgb = pil_image.convert("RGB")
    width, height = rgb.size

    if width < 8 or height < 8:
        raise ImageValidationError(
            "INVALID_IMAGE",
            "Image dimensions are too small (minimum 8x8).",
        )

    return ValidatedImage(image=rgb, width=width, height=height, mime_type=mime_type)
