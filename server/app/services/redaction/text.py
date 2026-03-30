from __future__ import annotations

from app.models.job import EntityRecord


def redact_text(text: str, entities: list[EntityRecord], token: str) -> str:
    """Replace character spans from end to start so indices remain valid."""
    spans = sorted(((e.start, e.end) for e in entities), reverse=True)
    out = text
    for start, end in spans:
        if start < 0 or end > len(out) or start >= end:
            continue
        out = out[:start] + token + out[end:]
    return out
