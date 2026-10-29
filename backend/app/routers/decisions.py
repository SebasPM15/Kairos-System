from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.decision import DecisionCreate, DecisionRead
from app.services.decision_service import DecisionService
from app.services.errors import DecisionNotFound, ProjectNotFound

router = APIRouter(tags=["decisions"])


def get_decision_service(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DecisionService:
    return DecisionService(db, user.id)


@contextmanager
def _http_errors() -> Iterator[None]:
    try:
        yield
    except ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    except DecisionNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision not found")


@router.get("/projects/{project_id}/decisions", response_model=list[DecisionRead])
def list_decisions(project_id: int, service: DecisionService = Depends(get_decision_service)):
    with _http_errors():
        return service.list(project_id)


@router.post(
    "/projects/{project_id}/decisions",
    response_model=DecisionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_decision(
    project_id: int,
    data: DecisionCreate,
    service: DecisionService = Depends(get_decision_service),
):
    with _http_errors():
        return service.create(project_id, data)


@router.delete("/decisions/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_decision(decision_id: int, service: DecisionService = Depends(get_decision_service)):
    with _http_errors():
        service.delete(decision_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
