from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.config import Settings
from app.models.job import (
    AuditRecord,
    DocumentType,
    ErrorInfo,
    JobCreateRequest,
    JobRecord,
    JobStatus,
    ProcessingResultMetadata,
)
from app.services.pipeline.processor import DocumentProcessor
from app.services.protocols import JobRepository, ObjectStorage

logger = logging.getLogger(__name__)

# Single logical partition for the in-memory object store.
_STORE_PARTITION = "memory"


class JobService:
    """Create jobs (in-memory), object bytes in process RAM; processing is synchronous."""

    def __init__(
        self,
        settings: Settings,
        jobs: JobRepository,
        storage: ObjectStorage,
        processor: DocumentProcessor,
    ) -> None:
        self._settings = settings
        self._jobs = jobs
        self._storage = storage
        self._processor = processor

    def create_job(self, req: JobCreateRequest) -> JobRecord:
        job_id = str(uuid.uuid4())
        raw_key = f"raw/{job_id}/{req.filename}"
        job = JobRecord(
            job_id=job_id,
            status=JobStatus.received,
            document_type=req.document_type,
            content_type=req.content_type,
            original_filename=req.filename,
            raw_bucket=_STORE_PARTITION,
            raw_key=raw_key,
            audit=AuditRecord(
                submitter_id=req.submitter_id,
                submitted_at=datetime.now(UTC),
            ),
        )
        self._jobs.put(job)
        return job

    def upload_raw_bytes(
        self,
        job_id: str,
        body: bytes,
        *,
        content_type: str | None,
    ) -> JobRecord:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        if job.raw_bucket is None or job.raw_key is None:
            raise ValueError("Job missing raw object location")
        self._storage.put_object(
            job.raw_bucket,
            job.raw_key,
            body,
            content_type=content_type,
        )
        updated = job.model_copy(update={"status": JobStatus.queued, "content_type": content_type})
        self._jobs.update(updated)
        return updated

    def run_pipeline(self, job_id: str) -> JobRecord:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        raw_bucket = job.raw_bucket
        raw_key = job.raw_key
        if raw_bucket is None or raw_key is None:
            raise ValueError("Job missing raw object location")
        job = job.model_copy(update={"status": JobStatus.processing})
        self._jobs.update(job)

        try:
            raw = self._storage.get_object(raw_bucket, raw_key)
            result, redacted_bytes, meta_bytes = self._processor.process(
                job.document_type,
                raw,
                job_id=job_id,
            )
            ext = ".txt"
            if job.document_type is DocumentType.pdf:
                ext = ".pdf"
            elif job.document_type is DocumentType.image:
                ext = ".png"
            red_key = f"redacted/{job_id}/document{ext}"
            meta_key = f"metadata/{job_id}/entities.json"

            self._storage.put_object(_STORE_PARTITION, red_key, redacted_bytes)
            self._storage.put_object(
                _STORE_PARTITION,
                meta_key,
                meta_bytes,
                content_type="application/json",
            )

            final = job.model_copy(
                update={
                    "status": result.status,
                    "redacted_bucket": _STORE_PARTITION,
                    "redacted_key": red_key,
                    "metadata_bucket": _STORE_PARTITION,
                    "metadata_key": meta_key,
                    "result": result,
                },
            )
            self._jobs.update(final)
            return final
        except Exception as exc:
            logger.exception("Pipeline failed for job %s", job_id)
            err = ErrorInfo(
                code="PIPELINE_ERROR",
                category="processing",
                message=str(type(exc).__name__),
            )
            failed = job.model_copy(update={"status": JobStatus.failed, "error": err})
            self._jobs.update(failed)
            return failed

    def get_job(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def process_sync(
        self,
        *,
        document_type: DocumentType,
        raw_bytes: bytes,
        submitter_id: str | None = None,
    ) -> tuple[ProcessingResultMetadata, bytes, bytes]:
        if len(raw_bytes) > self._settings.sync_max_bytes:
            raise ValueError("Payload exceeds sync_max_bytes")
        job_id = f"sync-{uuid.uuid4()}"
        result, redacted, meta = self._processor.process(document_type, raw_bytes, job_id=job_id)
        audit = result.audit.model_copy(
            update={"submitter_id": submitter_id, "submitted_at": datetime.now(UTC)},
        )
        result = result.model_copy(update={"audit": audit})
        return result, redacted, meta
