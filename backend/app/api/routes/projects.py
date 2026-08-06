from fastapi import APIRouter

from app.core.stubs import not_implemented
from app.schemas.projects import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(payload: ProjectCreate) -> ProjectResponse:
    not_implemented("§1.3 Upload & Project Flow")


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str) -> ProjectResponse:
    not_implemented("§1.3 Upload & Project Flow")


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, payload: ProjectCreate) -> ProjectResponse:
    not_implemented("§1.3 Upload & Project Flow")
