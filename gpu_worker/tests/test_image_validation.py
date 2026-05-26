import pytest
from PIL import Image
from io import BytesIO

from app.utils.image_validation import (
    ImageValidationError,
    decode_and_validate_image,
    validate_mime_type,
)


def _png_bytes(width: int = 64, height: int = 64) -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_validate_mime_type_rejects_unknown() -> None:
    with pytest.raises(ImageValidationError) as exc:
        validate_mime_type("image/bmp")
    assert exc.value.code == "INVALID_IMAGE"


def test_decode_valid_png() -> None:
    data = _png_bytes()
    result = decode_and_validate_image(data, "image/png")
    assert result.width == 64
    assert result.height == 64


def test_reject_oversized_resolution() -> None:
    data = _png_bytes(1200, 1200)
    with pytest.raises(ImageValidationError) as exc:
        decode_and_validate_image(data, "image/png")
    assert exc.value.code == "UNSUPPORTED_RESOLUTION"
