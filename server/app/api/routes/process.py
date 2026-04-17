from __future__ import annotations

import asyncio
import base64
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import RedactionServiceDep
from app.config import Settings, get_settings
from app.models.processing import DocumentType

router = APIRouter(prefix="/process", tags=["process"])


class SyncProcessResponse(BaseModel):
    result: dict[str, Any]
    redacted_base64: str


@router.post("/sync", response_model=SyncProcessResponse)
async def process_sync(
    svc: RedactionServiceDep,
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(...)],
    document_type: Annotated[str, Form(...)],
    submitter_id: Annotated[str, Form()] = "",
) -> SyncProcessResponse:
    """Process a small document in one request and return the redacted bytes."""
    raw = await file.read()
    if len(raw) > settings.sync_max_bytes:
        raise HTTPException(status_code=413, detail="File exceeds sync_max_bytes")

    try:
        dtype = DocumentType(document_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid document_type") from exc

    try:
        # Run the CPU / OCR work in a thread so the FastAPI event loop stays responsive.
        result, redacted, _metadata_bytes = await asyncio.wait_for(
            asyncio.to_thread(
                svc.process_document,
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

    # Return binary data as base64 so the sync API stays JSON-only.
    b64 = base64.standard_b64encode(redacted).decode("ascii")
    return SyncProcessResponse(result=result.model_dump(mode="json"), redacted_base64=b64)
