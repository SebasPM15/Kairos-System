from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.milestone import MilestoneCreate, MilestoneRead, MilestoneUpdate
from app.services.errors import MilestoneNotFound, ProjectNotFound
from app.services.milestone_service import MilestoneService

router = APIRouter(tags=["milestones"])


def get_milestone_service(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> MilestoneService:
    return MilestoneService(db, user.id)


@contextmanager
def _http_errors() -> Iterator[None]:
    try:
        yield
    except ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    except MilestoneNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Milestone not found")


@router.get("/projects/{project_id}/milestones", response_model=list[MilestoneRead])
def list_milestones(project_id: int, service: MilestoneService = Depends(get_milestone_service)):
    with _http_errors():
        return service.list(project_id)


@router.post(
    "/projects/{project_id}/milestones",
    response_model=MilestoneRead,
    status_code=status.HTTP_201_CREATED,
)
def create_milestone(
    project_id: int,
    data: MilestoneCreate,
    service: MilestoneService = Depends(get_milestone_service),
):
    with _http_errors():
        return service.create(project_id, data)


@router.patch("/milestones/{milestone_id}", response_model=MilestoneRead)
def update_milestone(
    milestone_id: int,
    data: MilestoneUpdate,
    service: MilestoneService = Depends(get_milestone_service),
):
    with _http_errors():
        return service.update(milestone_id, data)


@router.delete("/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_milestone(milestone_id: int, service: MilestoneService = Depends(get_milestone_service)):
    with _http_errors():
        service.delete(milestone_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
