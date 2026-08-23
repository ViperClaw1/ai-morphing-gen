import os
import time
from typing import Any

import torch
from diffusers import StableDiffusionImg2ImgPipeline
from loguru import logger

from app.core.config import Settings, get_settings
from app.utils.cuda_utils import assert_cuda_available, get_vram_usage_mb


class ModelLoadError(RuntimeError):
    """Raised when the diffusion pipeline cannot be loaded."""


class ModelLoader:
    """Singleton Stable Diffusion 1.5 img2img pipeline loader.

    Plain img2img only — no ControlNet conditioning yet, though
    docs/phase0_environment_setup.md already locked ControlNet (canny/openpose)
    as the identity-consistency method for 1.2. Tracked as a follow-up, not
    implemented here: swapping to StableDiffusionControlNetImg2ImgPipeline needs
    a conditioning-image preprocessor, a new dependency, and new request params.
    """

    _instance: "ModelLoader | None" = None

    def __new__(cls) -> "ModelLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._pipeline: StableDiffusionImg2ImgPipeline | None = None
        self._load_duration_ms: int | None = None
        self._initialized = True

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    @property
    def load_duration_ms(self) -> int | None:
        return self._load_duration_ms

    def get_pipeline(self) -> StableDiffusionImg2ImgPipeline:
        if self._pipeline is None:
            raise ModelLoadError("Model is not loaded. Startup preload may have failed.")
        return self._pipeline

    def load(self, settings: Settings | None = None) -> None:
        if self._pipeline is not None:
            return

        cfg = settings or get_settings()
        assert_cuda_available()

        os.environ.setdefault("HF_HOME", str(cfg.hf_home))
        cache_dir = str(cfg.model_cache_dir)
        os.makedirs(cache_dir, exist_ok=True)

        start = time.perf_counter()
        log = logger.bind(component="model_loader", model_id=cfg.model_id)

        try:
            log.info("Loading Stable Diffusion img2img pipeline")
            pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
                cfg.model_id,
                torch_dtype=torch.float16,
                safety_checker=None,
                requires_safety_checker=False,
                cache_dir=cache_dir,
                local_files_only=cfg.local_files_only,
            )
            pipeline = pipeline.to(cfg.device)
            pipeline.set_progress_bar_config(disable=True)

            if cfg.enable_xformers:
                try:
                    pipeline.enable_xformers_memory_efficient_attention()
                    log.info("xFormers memory efficient attention enabled")
                except Exception as exc:
                    log.warning("xFormers unavailable: {}", exc)

            self._pipeline = pipeline
            self._load_duration_ms = int((time.perf_counter() - start) * 1000)
            vram = get_vram_usage_mb()
            log.info(
                "Model loaded in {} ms | VRAM used: {} MB / {} MB",
                self._load_duration_ms,
                vram.get("used_mb"),
                vram.get("total_mb"),
            )
        except Exception as exc:
            self._pipeline = None
            log.exception("Model loading failed")
            raise ModelLoadError(f"Failed to load model: {exc}") from exc


def get_model_loader() -> ModelLoader:
    return ModelLoader()
