from __future__ import annotations

import fitz

from app.config import Settings
from app.models.processing import BoundingBox, DocumentType
from app.services.extraction.rekognition import RekognitionTextExtractor
from app.services.extraction.textract import TextractExtractor
from app.services.extraction.types import ExtractedBlock, ExtractionResult


class ExtractionService:
    """Route by document type.

    PyMuPDF for PDF text; Textract/Rekognition when configured.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._textract = TextractExtractor(settings)
        self._rekognition = RekognitionTextExtractor(settings)

    def extract(
        self,
        document_type: DocumentType,
        content: bytes,
    ) -> ExtractionResult:
        # Text files already arrive as bytes from the API, so decoding is enough.
        if document_type is DocumentType.text:
            text = content.decode("utf-8", errors="replace")
            return ExtractionResult(full_text=text, blocks=[ExtractedBlock(text=text, page=1)])

        if document_type is DocumentType.pdf:
            # Prefer the embedded text layer when it exists; OCR only when the PDF is scanned.
            pymupdf_result = self._extract_pdf_pymupdf(content)
            # Scanned PDFs have no text layer; use Textract OCR (requires AWS).
            if not pymupdf_result.full_text.strip():
                return self._textract.analyze_document_bytes(content)
            return pymupdf_result

        if document_type is DocumentType.image:
            # Images always need OCR before we can detect sensitive spans.
            return self._rekognition.detect_text(content)

        raise ValueError(f"Unsupported document type: {document_type}")

    def _extract_pdf_pymupdf(self, content: bytes) -> ExtractionResult:
        doc = fitz.open(stream=content, filetype="pdf")
        blocks: list[ExtractedBlock] = []
        parts: list[str] = []
        try:
            for page_index in range(len(doc)):
                page = doc[page_index]
                page_no = page_index + 1
                text_dict = page.get_text("dict")
                for b in text_dict.get("blocks", []):
                    if b.get("type") != 0:
                        continue
                    for line in b.get("lines", []):
                        line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                        if not line_text.strip():
                            continue
                        parts.append(line_text)
                        bbox_raw = line.get("bbox")
                        bbox = None
                        if bbox_raw and len(bbox_raw) == 4:
                            x0, y0, x1, y1 = bbox_raw
                            pw, ph = page.rect.width, page.rect.height
                            if pw > 0 and ph > 0:
                                bbox = BoundingBox(
                                    left=x0 / pw,
                                    top=y0 / ph,
                                    width=(x1 - x0) / pw,
                                    height=(y1 - y0) / ph,
                                )
                        blocks.append(
                            ExtractedBlock(
                                text=line_text,
                                page=page_no,
                                bounding_box=bbox,
                            ),
                        )
        finally:
            doc.close()
        full_text = "\n".join(parts)
        return ExtractionResult(full_text=full_text, blocks=blocks)
