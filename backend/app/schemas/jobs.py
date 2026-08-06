from pydantic import BaseModel


class JobResponse(BaseModel):
    """Every job status response carries these three fields — api-conventions.md."""

    job_id: str
    queue_name: str
    state: str  # queued | running | retrying | failed | completed
