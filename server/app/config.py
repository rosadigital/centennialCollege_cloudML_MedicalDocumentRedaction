from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application and AWS API configuration (env-driven; no secrets in code)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Medical Records Redaction API"
    debug: bool = False

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


def get_settings() -> Settings:
    return Settings()
