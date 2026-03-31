from __future__ import annotations

from typing import Any

import boto3

from app.config import Settings
from app.models.processing import EntityRecord


class ComprehendDetector:
    """Amazon Comprehend Medical (PHI) + Comprehend DetectPiiEntities."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._medical: Any | None = None
        self._comprehend: Any | None = None
        if settings.use_aws_comprehend:
            self._medical = boto3.client(
                "comprehendmedical",
                region_name=settings.aws_region,
            )
            self._comprehend = boto3.client("comprehend", region_name=settings.aws_region)

    def detect_all(self, text: str) -> list[EntityRecord]:
        if not self._settings.use_aws_comprehend or not self._medical or not self._comprehend:
            return []
        out: list[EntityRecord] = []
        out.extend(self._detect_phi(text))
        out.extend(self._detect_pii(text))
        return out

    def _detect_phi(self, text: str) -> list[EntityRecord]:
        assert self._medical is not None
        # Comprehend Medical has input size limits; chunk if needed.
        chunk_size = 20000
        results: list[EntityRecord] = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            resp = self._medical.detect_phi(Text=chunk)
            offset = i
            for ent in resp.get("Entities", []):
                begin = int(ent.get("BeginOffset", 0)) + offset
                end = int(ent.get("EndOffset", 0)) + offset
                results.append(
                    EntityRecord(
                        type=str(ent.get("Type", "PHI")),
                        confidence=float(ent.get("Score", 0.0)),
                        start=begin,
                        end=end,
                        page=None,
                        source="comprehend_medical",
                    ),
                )
        return results

    def _detect_pii(self, text: str) -> list[EntityRecord]:
        assert self._comprehend is not None
        chunk_size = 5000
        results: list[EntityRecord] = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            resp = self._comprehend.detect_pii_entities(Text=chunk, LanguageCode="en")
            offset = i
            for ent in resp.get("Entities", []):
                begin = int(ent.get("BeginOffset", 0)) + offset
                end = int(ent.get("EndOffset", 0)) + offset
                results.append(
                    EntityRecord(
                        type=str(ent.get("Type", "PII")),
                        confidence=float(ent.get("Score", 0.0)),
                        start=begin,
                        end=end,
                        page=None,
                        source="comprehend_pii",
                    ),
                )
        return results
