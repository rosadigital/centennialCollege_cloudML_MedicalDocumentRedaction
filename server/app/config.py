from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application and AWS API configuration (env-driven; no secrets in code)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Medical Records Redaction API"
    debug: bool = False
    # Comma-separated string so Docker/env_file works; pydantic-settings would
    # otherwise try JSON decoding for list[str] before validators run.
    cors_origins: str = Field(
        default="http://127.0.0.1:5500,http://localhost:5500",
        description="Comma-separated CORS origins for the frontend",
    )

    aws_region: str = Field(default="us-east-1", description="AWS region for boto3 clients")

    sync_max_bytes: int = Field(default=512_000, description="Max upload size for sync API")
    sync_max_seconds: float = Field(default=60.0, description="Max processing time for sync API")

    redaction_token: str = "[REDACTED]"

    confidence_review_threshold: float = Field(
        default=0.75,
        description="Entities below this max confidence may flag review_required",
    )

    use_aws_comprehend: bool = Field(
        default=False,
        description="If false, skip Comprehend calls (local dev / tests)",
    )

    @property
    def cors_allowed_origins(self) -> list[str]:
        items = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return items or ["http://127.0.0.1:5500", "http://localhost:5500"]


def get_settings() -> Settings:
    return Settings()
