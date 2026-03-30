from __future__ import annotations

from app.models.job import JobRecord


class MemoryJobRepository:
    """In-process job store (MVP; not persisted across restarts)."""

    def __init__(self) -> None:
        self._items: dict[str, JobRecord] = {}

    def put(self, job: JobRecord) -> None:
        self._items[job.job_id] = job

    def get(self, job_id: str) -> JobRecord | None:
        return self._items.get(job_id)

    def update(self, job: JobRecord) -> None:
        self.put(job)


class MemoryObjectStorage:
    """In-process byte store keyed by (partition, object_key)."""

    def __init__(self) -> None:
        self._objects: dict[tuple[str, str], bytes] = {}
        self._content_types: dict[tuple[str, str], str | None] = {}

    def put_object(
        self,
        bucket: str,
        key: str,
        body: bytes,
        *,
        content_type: str | None = None,
    ) -> None:
        self._objects[(bucket, key)] = body
        self._content_types[(bucket, key)] = content_type

    def get_object(self, bucket: str, key: str) -> bytes:
        return self._objects[(bucket, key)]
