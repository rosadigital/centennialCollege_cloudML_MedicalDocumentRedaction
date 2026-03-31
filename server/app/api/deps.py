from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from app.services.sync_redaction import SyncRedactionService


def get_redaction_service(request: Request) -> SyncRedactionService:
    return cast(SyncRedactionService, request.app.state.redaction_service)


RedactionServiceDep = Annotated[SyncRedactionService, Depends(get_redaction_service)]
