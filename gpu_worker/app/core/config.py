from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # This Settings class has real fields starting with "model_" (model_id,
        # model_variant, model_cache_dir) — clear pydantic's own reserved "model_"
        # namespace so it stops warning about the collision.
        protected_namespaces=(),
    )

    app_name: str = "AI Morphing GPU Worker"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    model_id: str = "runwayml/stable-diffusion-v1-5"
    # fp16 variant only — half the download/disk size of the default fp32 weights, and
    # matches torch_dtype=float16 below. The Dockerfile's snapshot_download must fetch this
    # same variant (see its allow_patterns) or local_files_only=True will fail to find it.
    model_variant: str = "fp16"
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

    # IP-Adapter FaceID: anchors identity (face embedding) during img2img so
    # strength/guidance/steps control style change without redrawing the face.
    ip_adapter_repo: str = "h94/IP-Adapter-FaceID"
    ip_adapter_weight_name: str = "ip-adapter-faceid_sd15.bin"
    ip_adapter_scale: float = 0.6
    insightface_model_name: str = "buffalo_l"
    insightface_root: Path = Field(default=Path("/app/models/insightface"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
