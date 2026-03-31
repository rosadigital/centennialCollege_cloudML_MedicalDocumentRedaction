from __future__ import annotations

from typing import Any

import boto3

from app.config import Settings
from app.services.extraction.types import ExtractedBlock, ExtractionResult


class TextractExtractor:
    """Amazon Textract integration for PDF/scanned OCR (sync helpers)."""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._settings = settings
        self._client: Any = client or boto3.client("textract", region_name=settings.aws_region)

    def analyze_document_bytes(self, document_bytes: bytes) -> ExtractionResult:
        """Run synchronous document analysis (suitable for single-page or small docs)."""
        resp = self._client.detect_document_text(Document={"Bytes": document_bytes})
        return self._blocks_from_response(resp)

    def _blocks_from_response(self, resp: dict[str, Any]) -> ExtractionResult:
        blocks_out: list[ExtractedBlock] = []
        lines: list[str] = []
        for block in resp.get("Blocks", []):
            if block.get("BlockType") != "LINE":
                continue
            text = block.get("Text", "")
            if not text:
                continue
            lines.append(text)
            geom = block.get("Geometry", {}).get("BoundingBox", {})
            bbox = None
            if geom:
                from app.models.processing import BoundingBox

                bbox = BoundingBox(
                    left=float(geom.get("Left", 0)),
                    top=float(geom.get("Top", 0)),
                    width=float(geom.get("Width", 0)),
                    height=float(geom.get("Height", 0)),
                )
            page = int(block.get("Page", 1))
            blocks_out.append(ExtractedBlock(text=text, page=page, bounding_box=bbox))
        full_text = "\n".join(lines)
        return ExtractionResult(full_text=full_text, blocks=blocks_out)
