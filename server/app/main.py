from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

from app.api.routes import health, jobs
from app.config import Settings
from app.services.job_service import JobService
from app.services.pipeline.processor import DocumentProcessor
from app.services.storage.memory import MemoryJobRepository, MemoryObjectStorage

if TYPE_CHECKING:
    from app.services.protocols import JobRepository, ObjectStorage


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    jobs_repo: JobRepository = MemoryJobRepository()
    storage: ObjectStorage = MemoryObjectStorage()
    processor = DocumentProcessor(settings)
    app.state.job_service = JobService(settings, jobs_repo, storage, processor)
    yield


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(jobs.router, prefix="/api/v1")
    return app


app = create_app()
