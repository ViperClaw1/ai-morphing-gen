from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str | None = None


class ProjectResponse(BaseModel):
    id: str
    title: str | None
    status: str
