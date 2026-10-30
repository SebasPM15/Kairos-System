from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas.config import PublicConfig

router = APIRouter(tags=["config"])


@router.get("/config", response_model=PublicConfig)
def read_config(settings: Settings = Depends(get_settings)):
    return PublicConfig(max_active_projects=settings.max_active_projects)
