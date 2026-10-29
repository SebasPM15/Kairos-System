from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.deps import get_current_user
from app.exporters.project_exporter import build_exporter
from app.models import User
from app.schemas.export import ExportSummary
from app.services.errors import UnsafeVaultPath, VaultNotConfigured

router = APIRouter(tags=["export"])


@contextmanager
def _http_errors() -> Iterator[None]:
    try:
        yield
    except VaultNotConfigured:
        raise HTTPException(status.HTTP_409_CONFLICT, "Obsidian vault is not configured")
    except UnsafeVaultPath:
        raise HTTPException(status.HTTP_409_CONFLICT, "Export path is outside the vault")


@router.post("/export", response_model=ExportSummary)
def export_vault(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    with _http_errors():
        return build_exporter(db, user.id, settings).export()
