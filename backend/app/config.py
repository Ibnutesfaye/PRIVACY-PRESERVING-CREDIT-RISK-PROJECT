from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ml.config import PROJECT_ROOT


class ApplicationSettings(BaseSettings):
    """Validated non-secret application and security-boundary configuration."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    application_environment: Literal["development", "test", "staging", "production"] = "development"
    application_service_name: str = "cipherscore-api"
    application_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    security_max_request_bytes: int = Field(default=50_000_000, ge=1_024, le=64_000_000)
    security_trust_proxy_headers: bool = False
    model_plaintext_prediction_enabled: bool = True
    openfhe_worker_timeout_seconds: int = Field(default=120, ge=5, le=600)
    openfhe_encrypted_api_enabled: bool = True
    openfhe_profile_id: str = "ckks-balanced-degree7-v1"
    openfhe_model_version: str = "logistic-regression-baseline-v1"
    openfhe_max_ciphertext_bundle_bytes: int = Field(default=40_000_000, ge=1_000_000, le=55_000_000)
    observability_metrics_token: SecretStr | None = None
    observability_metrics_token_file: Path | None = None

    @field_validator("application_service_name")
    @classmethod
    def validate_service_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or len(normalized) > 80:
            raise ValueError("APPLICATION_SERVICE_NAME must contain 1-80 characters")
        return normalized

    @field_validator("openfhe_profile_id")
    @classmethod
    def validate_profile_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or len(normalized) > 80:
            raise ValueError("OPENFHE_PROFILE_ID must contain 1-80 characters")
        return normalized

    @property
    def allowed_origins(self) -> list[str]:
        origins = [item.strip().rstrip("/") for item in self.application_allowed_origins.split(",")]
        return [item for item in origins if item]

    @property
    def resolved_metrics_token(self) -> str | None:
        if self.observability_metrics_token_file is not None:
            try:
                return self.observability_metrics_token_file.read_text(encoding="utf-8").strip()
            except OSError as error:
                raise ValueError("OBSERVABILITY_METRICS_TOKEN_FILE could not be read") from error
        return self.observability_metrics_token.get_secret_value() if self.observability_metrics_token else None

    @model_validator(mode="after")
    def validate_environment_policy(self) -> "ApplicationSettings":
        if not self.allowed_origins:
            raise ValueError("APPLICATION_ALLOWED_ORIGINS must contain at least one origin")
        if "*" in self.allowed_origins:
            raise ValueError("Wildcard CORS origins are not allowed")
        if self.application_environment == "production":
            if self.model_plaintext_prediction_enabled:
                raise ValueError("MODEL_PLAINTEXT_PREDICTION_ENABLED must be false in production")
            if not self.openfhe_encrypted_api_enabled:
                raise ValueError("OPENFHE_ENCRYPTED_API_ENABLED must be true in production")
            if any(origin.startswith("http://") for origin in self.allowed_origins):
                raise ValueError("Production CORS origins must use HTTPS")
            if self.resolved_metrics_token is None or len(self.resolved_metrics_token) < 32:
                raise ValueError("OBSERVABILITY_METRICS_TOKEN must contain at least 32 characters in production")
        return self


@lru_cache(maxsize=1)
def get_application_settings() -> ApplicationSettings:
    return ApplicationSettings()
