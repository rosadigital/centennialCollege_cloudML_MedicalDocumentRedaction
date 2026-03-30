from app.models.job import EntityRecord
from app.services.detection.merge import dedupe_non_overlapping, merge_entities


def test_merge_overlapping_prefers_union_and_max_confidence() -> None:
    a = EntityRecord(
        type="NAME",
        confidence=0.9,
        start=0,
        end=5,
        page=None,
        source="a",
    )
    b = EntityRecord(
        type="NAME",
        confidence=0.5,
        start=3,
        end=8,
        page=None,
        source="b",
    )
    merged = merge_entities([a, b])
    assert len(merged) == 1
    assert merged[0].start == 0
    assert merged[0].end == 8
    assert merged[0].confidence == 0.9


def test_dedupe_identical_spans() -> None:
    a = EntityRecord(
        type="EMAIL",
        confidence=0.9,
        start=10,
        end=20,
        page=None,
        source="r1",
    )
    b = EntityRecord(
        type="EMAIL",
        confidence=0.8,
        start=10,
        end=20,
        page=None,
        source="r2",
    )
    d = dedupe_non_overlapping([a, b])
    assert len(d) == 1
