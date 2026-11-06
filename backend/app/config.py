from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: str = ""
    telegram_allowed_user_id: int | None = None
    database_url: str = "sqlite:///./kairos.db"
    max_active_projects: int = 3
    obsidian_vault_path: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    timezone: str = "America/Guayaquil"
    reminders_enabled: bool = True
    # Days without activity before a project counts as stalled; idea and done never alert
    stale_days_active: int = Field(default=7, ge=1)
    stale_days_paused: int = Field(default=30, ge=1)
    reminder_repeat_days: int = Field(default=7, ge=1)
    reminder_max_repeats: int = Field(default=3, ge=1)
    # Quiet hours in TIMEZONE; the range may cross midnight
    reminder_quiet_start_hour: int = Field(default=21, ge=0, le=23)
    reminder_quiet_end_hour: int = Field(default=8, ge=0, le=23)

    @field_validator("telegram_allowed_user_id", mode="before")
    @classmethod
    def _empty_id_is_none(cls, value):
        # .env.example ships the variable empty
        return None if value == "" else value

    @field_validator("timezone")
    @classmethod
    def _timezone_must_exist(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(
                f"unknown IANA time zone {value!r} (e.g. America/Guayaquil); "
                "make sure the tzdata package is installed"
            ) from exc
        return value

    @model_validator(mode="after")
    def _quiet_hours_must_differ(self) -> "Settings":
        if self.reminder_quiet_start_hour == self.reminder_quiet_end_hour:
            raise ValueError("REMINDER_QUIET_START_HOUR and REMINDER_QUIET_END_HOUR must differ")
        return self

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
