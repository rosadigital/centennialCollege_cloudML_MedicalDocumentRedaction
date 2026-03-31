from __future__ import annotations

from typing import Any

import boto3

from app.config import Settings
from app.models.processing import BoundingBox
from app.services.extraction.types import ExtractedBlock, ExtractionResult


class RekognitionTextExtractor:
    """Amazon Rekognition DetectText for image-based text."""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._settings = settings
        self._client: Any = client or boto3.client("rekognition", region_name=settings.aws_region)

    def detect_text(self, image_bytes: bytes) -> ExtractionResult:
        resp = self._client.detect_text(Image={"Bytes": image_bytes})
        lines: list[str] = []
        blocks: list[ExtractedBlock] = []
        for det in resp.get("TextDetections", []):
            if det.get("Type") != "LINE":
                continue
            text = det.get("DetectedText", "")
            if not text:
                continue
            lines.append(text)
            geom = det.get("Geometry", {}).get("BoundingBox", {})
            bbox = BoundingBox(
                left=float(geom.get("Left", 0)),
                top=float(geom.get("Top", 0)),
                width=float(geom.get("Width", 0)),
                height=float(geom.get("Height", 0)),
            )
            blocks.append(ExtractedBlock(text=text, page=1, bounding_box=bbox))
        full_text = "\n".join(lines)
        return ExtractionResult(full_text=full_text, blocks=blocks)
