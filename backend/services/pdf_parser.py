"""
Backward-compatible PDF text extraction wrapper.

This module delegates to the robust pdf_extraction pipeline
but exposes the same simple API for existing callers.
"""

from backend.services.pdf_extraction import extract_document


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file.

    Legacy API — returns the full concatenated text as a single string.
    Internally uses the robust multi-strategy extraction pipeline.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Cleaned, structured text with page markers.
    """
    doc = extract_document(file_path)
    return doc.full_text
