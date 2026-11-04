from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator
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

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
