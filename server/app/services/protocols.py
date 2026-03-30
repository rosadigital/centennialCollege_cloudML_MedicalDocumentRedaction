from __future__ import annotations

from typing import Protocol

from app.models.job import JobRecord


class JobRepository(Protocol):
    def put(self, job: JobRecord) -> None:
        """Create or replace job record."""

    def get(self, job_id: str) -> JobRecord | None:
        """Load job by id."""

    def update(self, job: JobRecord) -> None:
        """Persist job updates (full replace for simplicity)."""


class ObjectStorage(Protocol):
    def put_object(
        self,
        bucket: str,
        key: str,
        body: bytes,
        *,
        content_type: str | None = None,
    ) -> None:
        """Store object bytes in the in-memory store."""

    def get_object(self, bucket: str, key: str) -> bytes:
        """Read object bytes."""
