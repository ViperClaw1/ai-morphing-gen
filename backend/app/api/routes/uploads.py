from fastapi import APIRouter, File, UploadFile

from app.core.stubs import not_implemented
from app.schemas.uploads import AssetResponse

# Prefixed under /projects (not /uploads) to match the nested resource path in
# api-conventions.md: POST /projects/{id}/assets.
router = APIRouter(prefix="/projects", tags=["uploads"])


@router.post("/{project_id}/assets", response_model=AssetResponse, status_code=201)
async def upload_asset(project_id: str, file: UploadFile = File(...)) -> AssetResponse:  # noqa: B008 (FastAPI's own idiom)
    # §1.3 owns: MIME/signature validation, size limit, NSFW gate, face-detection gate,
    # auto-delete-after-processing. None of that belongs here until it lands together.
    not_implemented("§1.3 Upload & Project Flow")
