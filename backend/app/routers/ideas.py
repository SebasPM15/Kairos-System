from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.idea import IdeaCreate, IdeaRead, IdeaUpdate
from app.services.errors import IdeaNotFound, ProjectNotFound
from app.services.idea_service import IdeaService

router = APIRouter(tags=["ideas"])


def get_idea_service(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> IdeaService:
    return IdeaService(db, user.id)


@contextmanager
def _http_errors() -> Iterator[None]:
    try:
        yield
    except ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    except IdeaNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Idea not found")


@router.get("/projects/{project_id}/ideas", response_model=list[IdeaRead])
def list_project_ideas(project_id: int, service: IdeaService = Depends(get_idea_service)):
    with _http_errors():
        return service.list_by_project(project_id)


@router.post(
    "/projects/{project_id}/ideas",
    response_model=IdeaRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project_idea(
    project_id: int, data: IdeaCreate, service: IdeaService = Depends(get_idea_service)
):
    # The path decides the project; a conflicting body value is ignored
    with _http_errors():
        return service.create(data.model_copy(update={"project_id": project_id}))


@router.get("/ideas", response_model=list[IdeaRead])
def list_inbox(service: IdeaService = Depends(get_idea_service)):
    return service.list_inbox()


@router.post("/ideas", response_model=IdeaRead, status_code=status.HTTP_201_CREATED)
def create_idea(data: IdeaCreate, service: IdeaService = Depends(get_idea_service)):
    with _http_errors():
        return service.create(data)


@router.patch("/ideas/{idea_id}", response_model=IdeaRead)
def update_idea(idea_id: int, data: IdeaUpdate, service: IdeaService = Depends(get_idea_service)):
    with _http_errors():
        return service.update(idea_id, data)


@router.delete("/ideas/{idea_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_idea(idea_id: int, service: IdeaService = Depends(get_idea_service)):
    with _http_errors():
        service.delete(idea_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
