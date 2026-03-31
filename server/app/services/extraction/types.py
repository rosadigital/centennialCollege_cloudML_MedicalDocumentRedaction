from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.processing import BoundingBox


class ExtractedBlock(BaseModel):
    """Text segment with optional layout (§5.3.2)."""

    text: str
    page: int = 1
    line_index: int | None = None
    bounding_box: BoundingBox | None = None


class ExtractionResult(BaseModel):
    """Flattened extraction for downstream detection."""

    full_text: str
    blocks: list[ExtractedBlock] = Field(default_factory=list)
