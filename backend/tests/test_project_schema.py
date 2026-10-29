from datetime import UTC, datetime, timedelta, timezone

from app.schemas.project import ProjectRead


def read(last_activity_at: datetime) -> ProjectRead:
    return ProjectRead(
        id=1,
        name="A",
        slug="a",
        description="",
        status="idea",
        next_action=None,
        last_activity_at=last_activity_at,
        created_at=last_activity_at,
    )


def test_days_since_activity_counts_whole_days_in_utc():
    assert read(datetime.now(UTC) - timedelta(days=3, hours=2)).days_since_activity == 3
    assert read(datetime.now(UTC) - timedelta(hours=23)).days_since_activity == 0


def test_days_since_activity_ignores_the_input_utc_offset():
    # Same instant expressed in UTC+14 must give the same result as in UTC
    instant = datetime.now(UTC) - timedelta(days=2, hours=1)
    far_east = instant.astimezone(timezone(timedelta(hours=14)))

    assert read(far_east).days_since_activity == read(instant).days_since_activity == 2
