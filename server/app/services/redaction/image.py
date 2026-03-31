from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw

from app.models.processing import BoundingBox, EntityRecord
from app.services.extraction.types import ExtractionResult


def _box_to_pixels(bbox: BoundingBox, width: int, height: int) -> tuple[int, int, int, int]:
    left = int(bbox.left * width)
    top = int(bbox.top * height)
    right = int((bbox.left + bbox.width) * width)
    bottom = int((bbox.top + bbox.height) * height)
    return left, top, right, bottom


def redact_image_bytes(
    image_bytes: bytes,
    entities: list[EntityRecord],
    extraction: ExtractionResult,
) -> bytes:
    """Draw black boxes over OCR line regions that overlap entity text spans."""
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    offset = 0
    line_ranges: list[tuple[int, int, BoundingBox]] = []
    for i, block in enumerate(extraction.blocks):
        if i > 0:
            offset += 1
        start = offset
        end = offset + len(block.text)
        offset = end
        if block.bounding_box:
            line_ranges.append((start, end, block.bounding_box))

    for ent in entities:
        for start, end, bbox in line_ranges:
            if ent.end <= start or ent.start >= end:
                continue
            coords = _box_to_pixels(bbox, w, h)
            draw.rectangle(coords, fill=(0, 0, 0))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
