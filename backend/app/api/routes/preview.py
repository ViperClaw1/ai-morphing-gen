from fastapi import APIRouter

from app.core.stubs import not_implemented
from app.schemas.preview import (
    PreviewJobResponse,
    PreviewRequest,
    RenderJobResponse,
    RenderRequest,
)

router = APIRouter(prefix="/projects", tags=["preview"])


@router.post("/{project_id}/preview", response_model=PreviewJobResponse, status_code=202)
def create_preview(project_id: str, payload: PreviewRequest) -> PreviewJobResponse:
    not_implemented("§1.4 Preview Pipeline")


# /render lives here rather than a dedicated router file: implementation_plan.md §1.1 only
# calls out {projects,uploads,jobs,preview,billing,settings}.py, and this endpoint shares
# the preview pipeline's project-scoped video-job shape (enqueue → poll /jobs/{id}).
@router.post("/{project_id}/render", response_model=RenderJobResponse, status_code=202)
def create_render(project_id: str, payload: RenderRequest) -> RenderJobResponse:
    not_implemented("§1.6 Full Render Pipeline")
