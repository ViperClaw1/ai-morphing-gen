from typing import Any

from pydantic import BaseModel, Field


class RepairData(BaseModel):
    image_base64: str
    seed: int
    duration_ms: int
    mime_type: str = Field(default="image/png")


class ErrorDetail(BaseModel):
    code: str
    message: str


class SuccessResponse(BaseModel):
    success: bool = True
    data: RepairData | dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
