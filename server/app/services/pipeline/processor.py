from __future__ import annotations

import json
from datetime import UTC, datetime

from app.config import Settings
from app.models.job import (
    AuditRecord,
    DocumentType,
    JobStatus,
    ProcessingResultMetadata,
)
from app.services.detection.comprehend import ComprehendDetector
from app.services.detection.custom_rules import CustomRuleDetector
from app.services.detection.merge import dedupe_non_overlapping, merge_entities
from app.services.extraction.service import ExtractionService
from app.services.redaction.image import redact_image_bytes
from app.services.redaction.pdf import redact_pdf_bytes
from app.services.redaction.text import redact_text


class DocumentProcessor:
    """Extraction → detection → merge → optional review flag → redaction."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._extraction = ExtractionService(settings)
        self._comprehend = ComprehendDetector(settings)
        self._custom = CustomRuleDetector()

    def process(
        self,
        document_type: DocumentType,
        raw_bytes: bytes,
        *,
        job_id: str,
    ) -> tuple[ProcessingResultMetadata, bytes, bytes]:
        extraction = self._extraction.extract(document_type, raw_bytes)
        text = extraction.full_text
        custom_entities = self._custom.detect(text)
        managed_entities = self._comprehend.detect_all(text)
        combined = dedupe_non_overlapping(custom_entities + managed_entities)
        merged = merge_entities(combined)

        review = any(
            e.confidence < self._settings.confidence_review_threshold for e in merged
        )
        status = JobStatus.review_required if review else JobStatus.completed
        token = self._settings.redaction_token
        now = datetime.now(UTC)
        audit = AuditRecord(
            detector_versions={
                "custom_rules": "1.0.0",
                "comprehend": "enabled" if self._settings.use_aws_comprehend else "disabled",
            },
            processing_started_at=now,
            processing_completed_at=now,
            human_review_required=review,
        )

        if document_type is DocumentType.text:
            redacted = redact_text(text, merged, token).encode("utf-8")
        elif document_type is DocumentType.pdf:
            redacted = redact_pdf_bytes(
                raw_bytes,
                merged,
                text,
                blocks=extraction.blocks,
            )
        elif document_type is DocumentType.image:
            redacted = redact_image_bytes(raw_bytes, merged, extraction)
        else:
            raise ValueError(f"Unsupported document type: {document_type}")

        result = ProcessingResultMetadata(
            job_id=job_id,
            document_type=document_type,
            status=status,
            entities=merged,
            audit=audit,
        )
        meta_bytes = json.dumps(result.model_dump(mode="json"), indent=2).encode("utf-8")
        return result, redacted, meta_bytes
