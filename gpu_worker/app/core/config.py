from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Morphing GPU Worker"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    model_id: str = "runwayml/stable-diffusion-v1-5"
    model_cache_dir: Path = Field(default=Path("/app/models"))
    hf_home: Path = Field(default=Path("/app/models"))

    default_strength: float = 0.2
    default_guidance_scale: float = 5.0
    default_num_inference_steps: int = 25
    default_negative_prompt: str = (
        "blurry, distorted face, deformed, extra limbs, "
        "low quality, artifacts, wrong identity"
    )

    max_upload_bytes: int = 10 * 1024 * 1024
    max_inference_dimension: int = 1024
    resize_divisor: int = 8

    max_concurrent_inference: int = 1
    inference_timeout_seconds: float = 120.0

    device: str = "cuda"
    dtype: str = "float16"
    enable_xformers: bool = True
    local_files_only: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
