"""Application settings powered by Pydantic Settings v2.

Single source of truth for environment-driven configuration. Values are
validated at process startup; missing or invalid fields fail fast.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Secrets are wrapped in `SecretStr` so they never leak through `repr`,
    log formatters, or accidental serialisation.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "rcs-middleware"
    APP_ENV: Literal["dev", "staging", "prod"] = "dev"
    DEBUG: bool = True

    MYSQL_URL: str = Field(
        default="mysql+aiomysql://rcs:rcs@localhost:3306/rcs_middleware",
        description="Async DSN consumed by SQLAlchemy + aiomysql.",
    )
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    RCS_BASE_URL: str = Field(default="http://localhost:8080")
    RCS_APP_KEY: str = Field(default="change-me")
    RCS_APP_SECRET: SecretStr = Field(default=SecretStr("change-me"))
    RCS_API_VERSION: str = "1.0"
    RCS_TIMEOUT: float = 10.0

    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    API_KEY: SecretStr = Field(default=SecretStr("change-me"))
    WEBHOOK_SECRET: SecretStr = Field(default=SecretStr("change-me"))

    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])

    LOG_LEVEL: str = "INFO"
    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        # Allow comma-separated string in .env: "http://a.com,http://b.com"
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _prod_debug_must_be_false(self) -> "Settings":
        if self.APP_ENV == "prod" and self.DEBUG:
            raise ValueError("DEBUG must be False when APP_ENV=prod")
        return self

    @model_validator(mode="after")
    def _default_celery_to_redis(self) -> "Settings":
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor; tests can override via dependency injection."""
    return Settings()


settings = get_settings()
