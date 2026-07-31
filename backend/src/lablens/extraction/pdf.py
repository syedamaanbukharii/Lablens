"""PDF and image text extraction using PyMuPDF.

Unlike PAVE's doctr integration (which required torch and couldn't run in CI),
PyMuPDF extracts text from native PDFs with zero ML dependencies and handles
scanned PDFs via its built-in OCR bridge. It actually runs everywhere.
"""
from __future__ import annotations

from dataclasses import dataclass


import io
import logging

log = logging.getLogger(__name__)

@dataclass
class ExtractionResult:
    text: str
    pages: int = 0
    method: str = "unknown"
    confidence: float = 1.0


def extract_text_from_pdf(pdf_bytes: bytes) -> ExtractionResult:
    """Extract text from a PDF, falling back to OCR for scanned pages."""
    import fitz  # PyMuPDF
    
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_text = []
    has_text = False
    
    # Pass 1: Try native text extraction
    for page in doc:
        text = page.get_text("text").strip()
        if len(text) > 50:  # If we have substantial text, it's not purely a scan
            has_text = True
            pages_text.append(text)
    
    if has_text:
        doc.close()
        return ExtractionResult(
            text="\n\n".join(pages_text),
            pages=len(pages_text),
            method="pymupdf-text",
            confidence=0.95,
        )
        
    # Pass 2: Scanned PDF OCR fallback
    ocr_text = []
    try:
        import pytesseract
        from PIL import Image
        
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes()))
            text = pytesseract.image_to_string(img)
            if text.strip():
                ocr_text.append(text.strip())
                
        doc.close()
        if ocr_text:
            return ExtractionResult(
                text="\n\n".join(ocr_text),
                pages=len(ocr_text),
                method="tesseract-ocr",
                confidence=0.85,
            )
    except Exception as e:
        log.warning(f"OCR failed or tesseract not installed: {e}")
        
    doc.close()
    return ExtractionResult(
        text="(No text could be extracted. The PDF appears to be a scanned image and OCR is not available.)",
        pages=doc.page_count,
        method="error",
        confidence=0.0,
    )


def extract_text_from_image(image_bytes: bytes) -> ExtractionResult:
    """Extract text from a lab report image via OCR."""
    try:
        import pytesseract
        from PIL import Image
        
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        
        if text.strip():
            return ExtractionResult(
                text=text.strip(),
                pages=1,
                method="tesseract-image",
                confidence=0.85,
            )
    except Exception as e:
        log.warning(f"Image OCR failed or tesseract not installed: {e}")
        
    return ExtractionResult(
        text="(Image OCR failed. Tesseract may not be installed on the server. Please upload a text-based PDF.)",
        pages=1,
        method="error",
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
