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
