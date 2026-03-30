from __future__ import annotations

import re

from app.models.job import EntityRecord

# Canadian SIN-like pattern (9 digits with optional separators); tune per policy.
_SIN_PATTERN = re.compile(
    r"\b\d{3}[-\s]?\d{3}[-\s]?\d{3}\b",
)
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
)
_PHONE_PATTERN = re.compile(
    r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
)


class CustomRuleDetector:
    """Regex / dictionary-style detection (§5.4.2)."""

    def __init__(self, extra_patterns: dict[str, re.Pattern[str]] | None = None) -> None:
        self._patterns: dict[str, re.Pattern[str]] = {
            "SIN": _SIN_PATTERN,
            "EMAIL": _EMAIL_PATTERN,
            "PHONE": _PHONE_PATTERN,
        }
        if extra_patterns:
            self._patterns.update(extra_patterns)

    def detect(self, text: str) -> list[EntityRecord]:
        found: list[EntityRecord] = []
        for label, pattern in self._patterns.items():
            for m in pattern.finditer(text):
                found.append(
                    EntityRecord(
                        type=label,
                        confidence=0.9,
                        start=m.start(),
                        end=m.end(),
                        page=None,
                        source="custom_rules",
                    ),
                )
        return found
