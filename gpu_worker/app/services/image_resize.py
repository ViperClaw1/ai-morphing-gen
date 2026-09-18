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

    width, height = image.size
    new_width = _round_to_divisor(width, divisor)
    new_height = _round_to_divisor(height, divisor)

    if (new_width, new_height) != image.size:
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    return image, (new_width, new_height)
