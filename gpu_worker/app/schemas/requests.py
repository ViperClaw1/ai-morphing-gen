from pydantic import BaseModel, Field


class RepairParams(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Repair prompt describing desired frame quality.",
    )
    negative_prompt: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional negative prompt override.",
    )
    seed: int = Field(..., ge=0, le=2**32 - 1)
    strength: float = Field(default=0.2, ge=0.0, le=1.0)
    guidance_scale: float = Field(default=5.0, ge=0.0, le=30.0)
    num_inference_steps: int = Field(default=25, ge=1, le=150)
