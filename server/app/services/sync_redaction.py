from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from app.config import Settings
from app.models.processing import (
    DocumentType,
    ProcessingResultMetadata,
)
from app.services.pipeline.processor import DocumentProcessor


class SyncRedactionService:
    """Thin service wrapper for the one synchronous API flow we keep."""

    def __init__(self, settings: Settings, processor: DocumentProcessor) -> None:
        self._settings = settings
        self._processor = processor

    def process_document(
        self,
        *,
        document_type: DocumentType,
        raw_bytes: bytes,
        submitter_id: str | None = None,
    ) -> tuple[ProcessingResultMetadata, bytes, bytes]:
        if len(raw_bytes) > self._settings.sync_max_bytes:
            raise ValueError("Payload exceeds sync_max_bytes")

        # Generate one traceable id per request even though we no longer keep jobs.
        request_id = f"sync-{uuid.uuid4()}"
        result, redacted, _ = self._processor.process(
            document_type,
            raw_bytes,
            request_id=request_id,
        )

        # Fill audit fields that belong to the HTTP request rather than the processor.
        audit = result.audit.model_copy(
            update={"submitter_id": submitter_id, "submitted_at": datetime.now(UTC)},
        )
        result = result.model_copy(update={"audit": audit})
        metadata_bytes = json.dumps(result.model_dump(mode="json"), indent=2).encode("utf-8")
        return result, redacted, metadata_bytes
