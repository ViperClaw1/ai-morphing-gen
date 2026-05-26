from PIL import Image

from app.core.config import get_settings


def _round_to_divisor(value: int, divisor: int) -> int:
    return max(divisor, (value // divisor) * divisor)


def resize_for_inference(image: Image.Image) -> tuple[Image.Image, tuple[int, int]]:
    """
    Resize image so width and height are divisible by 8 while preserving aspect ratio.
    Never upscale beyond original dimensions unless required for divisor alignment.
    """
    settings = get_settings()
    divisor = settings.resize_divisor
    max_dim = settings.max_inference_dimension

    width, height = image.size
    scale = min(1.0, max_dim / max(width, height))
    if scale < 1.0:
        width = int(width * scale)
        height = int(height * scale)

    new_width = _round_to_divisor(width, divisor)
    new_height = _round_to_divisor(height, divisor)

    if new_width > max_dim:
        new_width = (max_dim // divisor) * divisor
    if new_height > max_dim:
        new_height = (max_dim // divisor) * divisor

    if (new_width, new_height) != image.size:
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    return image, (new_width, new_height)
