import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from app.models.base import UTCDateTime

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def alembic(tmp_path):
    database = tmp_path / "migrations.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{database}"}

    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
        )

    run.database = database
    return run


def test_upgrade_head_on_empty_database_creates_all_tables(alembic):
    result = alembic("upgrade", "head")

    assert result.returncode == 0, result.stderr
    with sqlite3.connect(alembic.database) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    assert {"users", "projects", "milestones", "ideas", "decisions"} <= tables


def test_models_match_migrations(alembic):
    assert alembic("upgrade", "head").returncode == 0

    result = alembic("check")

    assert result.returncode == 0, result.stdout + result.stderr


def test_utc_datetime_rejects_naive_values():
    with pytest.raises(ValueError, match="naive"):
        UTCDateTime().process_bind_param(datetime(2026, 1, 1), None)
