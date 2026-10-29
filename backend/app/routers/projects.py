from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.errors import ActiveLimitReached, NextActionRequired, ProjectNotFound
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ProjectService:
    return ProjectService(db, user.id, settings)


@contextmanager
def _http_errors() -> Iterator[None]:
    try:
        yield
    except ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    except ActiveLimitReached:
        raise HTTPException(status.HTTP_409_CONFLICT, "Active project limit reached")
    except NextActionRequired:
        raise HTTPException(422, "next_action is required to activate")


@router.get("", response_model=list[ProjectRead])
def list_projects(service: ProjectService = Depends(get_project_service)):
    return service.list()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, service: ProjectService = Depends(get_project_service)):
    return service.create(data)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, service: ProjectService = Depends(get_project_service)):
    with _http_errors():
        return service.get(project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int, data: ProjectUpdate, service: ProjectService = Depends(get_project_service)
):
    with _http_errors():
        return service.update(project_id, data)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, service: ProjectService = Depends(get_project_service)):
    with _http_errors():
        service.delete(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
