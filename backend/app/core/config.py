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

    app_name: str = "AI Morphing Generator API"
    env: str = "development"
    log_level: str = "INFO"

    # SQLite for MVP; POSTGRES_URL takes over in Phase 2 (docs/implementation_plan.md §2.1) —
    # postgres_url stays unused until that migration, kept here so the field exists ahead of it.
    sqlite_path: Path = Field(default=Path("./data/app.db"))
    postgres_url: str | None = None

    # RQ (Redis Queue) — not Celery, see CLAUDE.md architecture rules.
    redis_url: str = "redis://localhost:6379/0"

    # GPU worker (RunPod serverless), provisioned in §1.2.
    runpod_api_key: str = ""
    runpod_endpoint_id: str = ""

    # Object storage — Cloudflare R2 (S3-compatible).
    storage_path: Path = Field(default=Path("./storage"))  # local dev fallback only
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_endpoint: str = ""

    preview_enabled: bool = True
    preview_ttl_hours: int = 3
    preview_limit_per_project: int = 3

    # Comma-separated rather than a native list field: pydantic-settings expects JSON syntax
    # for list-typed env vars, which makes a plain CORS_ALLOWED_ORIGINS=a,b awkward to write.
    cors_allowed_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
