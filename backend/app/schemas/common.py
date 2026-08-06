from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Shape mandated by .claude/rules/api-conventions.md — every error response uses this,
    never a raw stack trace or FastAPI's default {"detail": ...}."""

    error: str
    code: str
