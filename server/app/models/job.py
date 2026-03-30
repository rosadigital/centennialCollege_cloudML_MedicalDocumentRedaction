from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    received = "received"
    queued = "queued"
    processing = "processing"
    review_required = "review_required"
    completed = "completed"
    failed = "failed"


class DocumentType(StrEnum):
    text = "text"
    pdf = "pdf"
    image = "image"


class BoundingBox(BaseModel):
    """Normalized page coordinates (0–1), when available."""

    left: float
    top: float
    width: float
    height: float


class EntityRecord(BaseModel):
    """Single detected entity aligned with §5.6 / §5.4.3."""

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


class ErrorInfo(BaseModel):
    """Failure details without raw PHI."""

    code: str
    category: str
    message: str


class AuditRecord(BaseModel):
    """Immutable-oriented audit fields (§6.2)."""

    submitter_id: str | None = None
    submitted_at: datetime | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    detector_versions: dict[str, str] = Field(default_factory=dict)
    rule_pack_version: str | None = None
    human_review_required: bool = False
    human_review_completed: bool = False


class ProcessingResultMetadata(BaseModel):
    """Job processing metadata + entity list (§5.6)."""

    job_id: str
    document_type: DocumentType
    status: JobStatus
    entities: list[EntityRecord] = Field(default_factory=list)
    processing_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    audit: AuditRecord = Field(default_factory=AuditRecord)


class JobRecord(BaseModel):
    """Job state and in-memory object pointers (partition + key)."""

    job_id: str
    status: JobStatus
    document_type: DocumentType
    content_type: str | None = None
    original_filename: str | None = None

    raw_bucket: str | None = None
    raw_key: str | None = None
    redacted_bucket: str | None = None
    redacted_key: str | None = None
    metadata_bucket: str | None = None
    metadata_key: str | None = None

    result: ProcessingResultMetadata | None = None
    error: ErrorInfo | None = None
    audit: AuditRecord = Field(default_factory=AuditRecord)

    extra: dict[str, Any] = Field(default_factory=dict)


class JobCreateRequest(BaseModel):
    """Client metadata before multipart upload to the API."""

    document_type: DocumentType
    filename: str
    content_type: str
    submitter_id: str | None = None
