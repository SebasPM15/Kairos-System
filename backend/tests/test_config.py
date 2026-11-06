import pytest
from pydantic import ValidationError

from app.config import Settings


def test_timezone_defaults_to_guayaquil() -> None:
    assert Settings().timezone == "America/Guayaquil"


def test_valid_timezone_is_accepted() -> None:
    assert Settings(timezone="America/New_York").tzinfo.key == "America/New_York"


def test_unknown_timezone_fails_with_a_clear_message() -> None:
    with pytest.raises(ValidationError, match="unknown IANA time zone 'Mars/Olympus'"):
        Settings(timezone="Mars/Olympus")


def test_reminder_defaults() -> None:
    settings = Settings()

    assert (settings.stale_days_active, settings.stale_days_paused) == (7, 30)
    assert (settings.reminder_repeat_days, settings.reminder_max_repeats) == (7, 3)
    assert (settings.reminder_quiet_start_hour, settings.reminder_quiet_end_hour) == (21, 8)
    assert settings.reminders_enabled is True


@pytest.mark.parametrize("field", ["stale_days_active", "stale_days_paused", "reminder_repeat_days", "reminder_max_repeats"])
def test_reminder_days_must_be_at_least_one(field) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: 0})


@pytest.mark.parametrize("field", ["reminder_quiet_start_hour", "reminder_quiet_end_hour"])
@pytest.mark.parametrize("hour", [-1, 24])
def test_quiet_hours_must_be_between_0_and_23(field, hour) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: hour})


def test_quiet_start_equal_to_end_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must differ"):
        Settings(reminder_quiet_start_hour=8, reminder_quiet_end_hour=8)


def test_quiet_hours_may_cross_midnight() -> None:
    settings = Settings(reminder_quiet_start_hour=22, reminder_quiet_end_hour=6)

    assert settings.reminder_quiet_start_hour > settings.reminder_quiet_end_hour
