from __future__ import annotations

import asyncio
import base64
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import JobServiceDep
from app.config import Settings, get_settings
from app.models.job import DocumentType, JobCreateRequest, JobRecord

router = APIRouter(prefix="/jobs", tags=["jobs"])


class CreateJobResponse(BaseModel):
    job_id: str
    raw_bucket: str | None
    raw_key: str | None
    status: str


class SyncProcessResponse(BaseModel):
    result: dict[str, Any]
    redacted_base64: str


@router.post("", response_model=CreateJobResponse)
def create_job(body: JobCreateRequest, svc: JobServiceDep) -> CreateJobResponse:
    job = svc.create_job(body)
    return CreateJobResponse(
        job_id=job.job_id,
        raw_bucket=job.raw_bucket,
        raw_key=job.raw_key,
        status=job.status.value,
    )


@router.get("/{job_id}", response_model=JobRecord)
def get_job(job_id: str, svc: JobServiceDep) -> JobRecord:
    job = svc.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/upload")
async def upload_raw(
    job_id: str,
    svc: JobServiceDep,
    file: UploadFile = File(...),
) -> dict[str, str]:
    """Upload raw bytes, then run the pipeline and wait for the result (MVP synchronous)."""
    body = await file.read()
    ct = file.content_type
    try:
        svc.upload_raw_bytes(job_id, body, content_type=ct)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found") from None
    job = svc.run_pipeline(job_id)
    return {"status": job.status.value, "job_id": job_id}


@router.post("/{job_id}/process")
def process_job(job_id: str, svc: JobServiceDep) -> dict[str, str]:
    """Run pipeline after raw object exists (waits until complete)."""
    job = svc.run_pipeline(job_id)
    return {"status": job.status.value, "job_id": job_id}


@router.post("/process/sync", response_model=SyncProcessResponse)
async def process_sync(
    svc: JobServiceDep,
    settings: Annotated[Settings, Depends(get_settings)],
    file: UploadFile = File(...),
    document_type: str = Form(...),
    submitter_id: str = Form(default=""),
) -> SyncProcessResponse:
    """Synchronous processing for small payloads (§5.2.2)."""
    raw = await file.read()
    if len(raw) > settings.sync_max_bytes:
        raise HTTPException(status_code=413, detail="File exceeds sync_max_bytes")
    try:
        dtype = DocumentType(document_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid document_type") from exc

    try:
        meta, redacted, _meta_bytes = await asyncio.wait_for(
            asyncio.to_thread(
                svc.process_sync,
                document_type=dtype,
                raw_bytes=raw,
                submitter_id=submitter_id or None,
            ),
            timeout=settings.sync_max_seconds,
        )
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Processing exceeded sync_max_seconds",
        ) from None

    b64 = base64.standard_b64encode(redacted).decode("ascii")
    return SyncProcessResponse(result=meta.model_dump(mode="json"), redacted_base64=b64)
