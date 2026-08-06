from pydantic import BaseModel


class PublicSettingsResponse(BaseModel):
    preview_enabled: bool
    preview_limit_per_project: int
    preview_ttl_hours: int
