from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, process
from app.config import Settings
from app.services.pipeline.processor import DocumentProcessor
from app.services.sync_redaction import SyncRedactionService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    processor = DocumentProcessor(settings)
    # Keep one shared service instance; the app only exposes the synchronous flow.
    app.state.redaction_service = SyncRedactionService(settings, processor)
    yield


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(process.router, prefix="/api/v1")
    return app


app = create_app()
