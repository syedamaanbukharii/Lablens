"""PDF and image text extraction using PyMuPDF.

Unlike PAVE's doctr integration (which required torch and couldn't run in CI),
PyMuPDF extracts text from native PDFs with zero ML dependencies and handles
scanned PDFs via its built-in OCR bridge. It actually runs everywhere.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExtractionResult:
    text: str
    pages: int = 0
    method: str = "unknown"
    confidence: float = 1.0


def extract_text_from_pdf(pdf_bytes: bytes) -> ExtractionResult:
    """Extract text from a PDF using PyMuPDF."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text.strip())

    doc.close()

    if pages:
        return ExtractionResult(
            text="\n\n".join(pages),
            pages=len(pages),
            method="pymupdf-text",
            confidence=0.95,
        )

    # Fallback: if no text found (scanned PDF), try OCR via PyMuPDF's built-in
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    ocr_pages = []
    for page in doc:
        # Render page to image and extract via blocks
        blocks = page.get_text("blocks")
        block_text = " ".join(b[4] for b in blocks if b[6] == 0)  # type 0 = text
        if block_text.strip():
            ocr_pages.append(block_text.strip())

    doc.close()

    return ExtractionResult(
        text="\n\n".join(ocr_pages) if ocr_pages else "(No text could be extracted from this PDF.)",
        pages=len(ocr_pages),
        method="pymupdf-blocks",
        confidence=0.75 if ocr_pages else 0.0,
    )


def extract_text_from_image(image_bytes: bytes) -> ExtractionResult:
    """Extract text from a lab report image. Placeholder for OCR integration."""
    # In production: integrate Tesseract, EasyOCR, or doctr here
    return ExtractionResult(
        text="(Image OCR not yet implemented. Please upload a PDF for best results.)",
        pages=1,
        method="placeholder",
        confidence=0.0,
    )


def extract_text(file_bytes: bytes, filename: str) -> ExtractionResult:
    """Route to the right extractor based on file type."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    if lower.endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        return extract_text_from_image(file_bytes)
    # Try as plain text
    try:
        text = file_bytes.decode("utf-8")
        return ExtractionResult(text=text, pages=1, method="plaintext", confidence=1.0)
    except UnicodeDecodeError:
        return ExtractionResult(text="(Unsupported file format.)", method="error", confidence=0.0)
