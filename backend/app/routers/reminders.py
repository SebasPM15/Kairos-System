from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.reminder import ReminderPrefsRead, ReminderPrefsUpdate, RemindersRead
from app.services.errors import ProjectNotFound
from app.services.reminder_service import ReminderService

router = APIRouter(tags=["reminders"])


def get_reminder_service(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ReminderService:
    return ReminderService(db, user.id, settings)


@router.get("/reminders", response_model=RemindersRead)
def list_reminders(service: ReminderService = Depends(get_reminder_service)):
    return service.overview()


@router.patch("/projects/{project_id}/reminders", response_model=ReminderPrefsRead)
def update_project_reminders(
    project_id: int,
    data: ReminderPrefsUpdate,
    service: ReminderService = Depends(get_reminder_service),
):
    try:
        return service.update_prefs(project_id, data)
    except ProjectNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
