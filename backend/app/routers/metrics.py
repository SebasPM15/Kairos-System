from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.metrics import MetricsRead
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


def get_metrics_service(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> MetricsService:
    return MetricsService(db, user.id, settings)


@router.get("", response_model=MetricsRead)
def read_metrics(
    weeks: int = Query(12, ge=1, le=52),
    service: MetricsService = Depends(get_metrics_service),
):
    return service.get(weeks)
