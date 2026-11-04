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


def test_assigned_at_backfill_uses_created_at_only_for_assigned_ideas(alembic):
    assert alembic("upgrade", "b7d2e41a9c15").returncode == 0
    with sqlite3.connect(alembic.database) as connection:
        connection.execute("INSERT INTO users (id, created_at) VALUES (1, '2026-01-01 00:00:00')")
        connection.execute(
            "INSERT INTO projects (id, user_id, name, slug, description, status, created_at, last_activity_at) "
            "VALUES (1, 1, 'P', 'p', '', 'idea', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
        )
        connection.executemany(
            "INSERT INTO ideas (id, user_id, project_id, content, created_at) VALUES (?, 1, ?, 'x', ?)",
            [(1, 1, "2026-02-03 10:00:00"), (2, None, "2026-02-04 11:00:00")],
        )

    result = alembic("upgrade", "head")

    assert result.returncode == 0, result.stderr
    with sqlite3.connect(alembic.database) as connection:
        rows = connection.execute("SELECT id, assigned_at FROM ideas ORDER BY id").fetchall()
        projects_survive = connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    assert rows == [(1, "2026-02-03 10:00:00"), (2, None)]
    assert projects_survive == 1


def test_assigned_at_downgrade_drops_the_column_and_keeps_ideas(alembic):
    assert alembic("upgrade", "head").returncode == 0
    with sqlite3.connect(alembic.database) as connection:
        connection.execute("INSERT INTO users (id, created_at) VALUES (1, '2026-01-01 00:00:00')")
        connection.execute(
            "INSERT INTO ideas (id, user_id, content, created_at) VALUES (1, 1, 'x', '2026-02-03 10:00:00')"
        )

    result = alembic("downgrade", "b7d2e41a9c15")

    assert result.returncode == 0, result.stderr
    with sqlite3.connect(alembic.database) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(ideas)")]
        count = connection.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]
    assert "assigned_at" not in columns
    assert count == 1
