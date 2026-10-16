from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from ml.config import PROJECT_ROOT


class AdminConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdminSettings:
    jwt_secret: str
    access_token_minutes: int
    refresh_token_days: int
    max_failed_logins: int
    lockout_minutes: int


class _AdminEnvironmentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    admin_jwt_secret: str = ""
    admin_jwt_secret_file: str = ""
    admin_access_token_minutes: int = Field(default=15, gt=0)
    admin_refresh_token_days: int = Field(default=7, gt=0)
    admin_max_failed_logins: int = Field(default=5, gt=0)
    admin_lockout_minutes: int = Field(default=15, gt=0)


def get_admin_settings() -> AdminSettings:
    try:
        configured = _AdminEnvironmentSettings()
    except ValidationError as error:
        raise AdminConfigurationError("Administrator security settings are invalid") from error
    if configured.admin_jwt_secret_file:
        try:
            with open(configured.admin_jwt_secret_file, encoding="utf-8") as stream:
                secret = stream.read().strip()
        except OSError as error:
            raise AdminConfigurationError("Administrator JWT secret file could not be read") from error
    else:
        secret = configured.admin_jwt_secret
    if len(secret) < 32:
        raise AdminConfigurationError(
            "ADMIN_JWT_SECRET must be configured with at least 32 characters"
        )
    return AdminSettings(
        jwt_secret=secret,
        access_token_minutes=configured.admin_access_token_minutes,
        refresh_token_days=configured.admin_refresh_token_days,
        max_failed_logins=configured.admin_max_failed_logins,
        lockout_minutes=configured.admin_lockout_minutes,
    )
