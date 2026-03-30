from __future__ import annotations

from typing import cast

import fitz

from app.models.job import BoundingBox, EntityRecord
from app.services.extraction.types import ExtractedBlock


def _bbox_to_rect(page: fitz.Page, bbox: BoundingBox) -> fitz.Rect:
    w, h = page.rect.width, page.rect.height
    x0 = bbox.left * w
    y0 = bbox.top * h
    x1 = (bbox.left + bbox.width) * w
    y1 = (bbox.top + bbox.height) * h
    return fitz.Rect(x0, y0, x1, y1)


def _line_ranges_for_blocks(
    blocks: list[ExtractedBlock],
) -> list[tuple[int, int, int, BoundingBox]]:
    """Map character ranges in joined full_text to (page, bbox) per line."""
    offset = 0
    ranges: list[tuple[int, int, int, BoundingBox]] = []
    for i, block in enumerate(blocks):
        if i > 0:
            offset += 1
        start = offset
        end = offset + len(block.text)
        offset = end
        if block.bounding_box is None:
            continue
        page_no = block.page if block.page is not None else 1
        ranges.append((start, end, page_no, block.bounding_box))
    return ranges


def _redact_layout(
    doc: fitz.Document,
    entities: list[EntityRecord],
    line_ranges: list[tuple[int, int, int, BoundingBox]],
) -> None:
    for ent in entities:
        for start, end, page_no, bbox in line_ranges:
            if ent.end <= start or ent.start >= end:
                continue
            page = doc[page_no - 1]
            rect = _bbox_to_rect(page, bbox)
            page.add_redact_annot(rect, fill=(0, 0, 0))


def _redact_search(doc: fitz.Document, entities: list[EntityRecord], full_text: str) -> None:
    for page in doc:
        for ent in entities:
            snippet = full_text[ent.start : ent.end].strip()
            if len(snippet) < 2:
                continue
            rects = page.search_for(snippet)
            for r in rects:
                page.add_redact_annot(r, fill=(0, 0, 0))


def redact_pdf_bytes(
    pdf_bytes: bytes,
    entities: list[EntityRecord],
    full_text: str,
    *,
    blocks: list[ExtractedBlock] | None = None,
) -> bytes:
    """Irreversible redaction: search-based for text PDFs, layout boxes for OCR/Textract."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        has_layout = bool(
            blocks and any(b.bounding_box is not None for b in blocks),
        )
        if has_layout:
            line_ranges = _line_ranges_for_blocks(blocks or [])
            _redact_layout(doc, entities, line_ranges)
        else:
            _redact_search(doc, entities, full_text)
        for page in doc:
            page.apply_redactions()
        return cast(bytes, doc.tobytes(deflate=True, garbage=4))
    finally:
        doc.close()
