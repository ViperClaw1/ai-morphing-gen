from pydantic import BaseModel


class AssetResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    order: int
