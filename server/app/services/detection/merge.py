from __future__ import annotations

from app.models.processing import EntityRecord


def _overlaps(a: EntityRecord, b: EntityRecord) -> bool:
    return not (a.end <= b.start or b.end <= a.start)


def merge_entities(entities: list[EntityRecord]) -> list[EntityRecord]:
    """Merge overlapping spans; prefer higher confidence and union bounds (§5.4.3)."""
    if not entities:
        return []
    ordered = sorted(entities, key=lambda e: (e.start, -e.confidence))
    merged: list[EntityRecord] = []
    for e in ordered:
        if not merged:
            merged.append(e)
            continue
        prev = merged[-1]
        if _overlaps(prev, e):
            merged[-1] = EntityRecord(
                type=prev.type if prev.confidence >= e.confidence else e.type,
                confidence=max(prev.confidence, e.confidence),
                start=min(prev.start, e.start),
                end=max(prev.end, e.end),
                page=prev.page if prev.page is not None else e.page,
                source=f"{prev.source}+{e.source}",
                bounding_box=e.bounding_box or prev.bounding_box,
            )
        else:
            merged.append(e)
    return merged


def dedupe_non_overlapping(entities: list[EntityRecord]) -> list[EntityRecord]:
    """Remove exact duplicate spans."""
    seen: set[tuple[int, int, str]] = set()
    out: list[EntityRecord] = []
    for e in entities:
        key = (e.start, e.end, e.type)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out
