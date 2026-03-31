from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ProcessingStatus(StrEnum):
    """Final status for a synchronous redaction request."""

    completed = "completed"
    review_required = "review_required"


class DocumentType(StrEnum):
    text = "text"
    pdf = "pdf"
    image = "image"


class BoundingBox(BaseModel):
    """Normalized page coordinates (0-1), when available."""

    left: float
    top: float
    width: float
    height: float


class EntityRecord(BaseModel):
    """Detected sensitive span in the extracted text."""

    type: str
    confidence: float = Field(ge=0.0, le=1.0)
    start: int
    end: int
    page: int | None = None
    source: str
    bounding_box: BoundingBox | None = None
    original_text_masked: str | None = Field(
        default=None,
        description="Optional masked representation per policy",
    )


class AuditRecord(BaseModel):
    """Operational metadata for one synchronous processing run."""

    submitter_id: str | None = None
    submitted_at: datetime | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    detector_versions: dict[str, str] = Field(default_factory=dict)
    rule_pack_version: str | None = None
    human_review_required: bool = False
    human_review_completed: bool = False


class ProcessingResultMetadata(BaseModel):
    """Structured result returned with the redacted document."""

    request_id: str
    document_type: DocumentType
    status: ProcessingStatus
    entities: list[EntityRecord] = Field(default_factory=list)
    processing_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    audit: AuditRecord = Field(default_factory=AuditRecord)
