from fastapi import APIRouter

from app.core.stubs import not_implemented
from app.schemas.jobs import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    not_implemented("§1.4 Preview Pipeline")
