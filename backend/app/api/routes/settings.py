from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.settings import PublicSettingsResponse

router = APIRouter(tags=["settings"])


@router.get("/settings/public", response_model=PublicSettingsResponse)
def get_public_settings() -> PublicSettingsResponse:
    # The one route in this batch that's genuinely done, not stubbed: it only echoes
    # config, no DB/queue dependency, so there's nothing left for a later phase to add.
    settings = get_settings()
    return PublicSettingsResponse(
        preview_enabled=settings.preview_enabled,
        preview_limit_per_project=settings.preview_limit_per_project,
        preview_ttl_hours=settings.preview_ttl_hours,
    )
