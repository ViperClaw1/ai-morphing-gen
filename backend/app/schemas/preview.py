from pydantic import BaseModel

from app.schemas.jobs import JobResponse


class PreviewRequest(BaseModel):
    style_preset: str = "default"


class PreviewJobResponse(JobResponse):
    project_id: str


class RenderRequest(BaseModel):
    pass


class RenderJobResponse(JobResponse):
    project_id: str
