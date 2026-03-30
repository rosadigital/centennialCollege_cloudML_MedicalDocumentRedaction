from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from app.services.job_service import JobService


def get_job_service(request: Request) -> JobService:
    return cast(JobService, request.app.state.job_service)


JobServiceDep = Annotated[JobService, Depends(get_job_service)]
