"""Resume text extraction utilities for PDF and DOCX files.

This module provides pure, side-effect-free functions that extract plain text
from resume attachments returned by the Greenhouse API. It is intentionally
decoupled from all Greenhouse API calls — callers are expected to supply raw
bytes (or base64-encoded bytes) directly.

Supported formats:
- PDF  — via pdfplumber
- DOCX — via python-docx
- Plain text — UTF-8 decode fallback

Both pdfplumber and python-docx are imported lazily inside each function so
that missing optional dependencies degrade gracefully rather than preventing
the module from loading.
"""
from __future__ import annotations

import base64
import io


def extract_text_from_pdf(content_bytes: bytes) -> str:
    """Extract plain text from a PDF file supplied as raw bytes.

    Iterates all pages and joins per-page text with double newlines. Pages
    that contain no extractable text are skipped. Returns an empty string if
    the bytes are not a valid PDF, if pdfplumber is not installed, or if no
    text can be extracted at all.

    Args:
        content_bytes: Raw bytes of a PDF file.

    Returns:
        Extracted text, or ``""`` on any error.
    """
    try:
        import pdfplumber  # noqa: PLC0415
    except ImportError:
        return ""

    try:
        with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
            page_texts: list[str] = []
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    page_texts.append(text.strip())
            return "\n\n".join(page_texts)
    except Exception:
        return ""


def extract_text_from_docx(content_bytes: bytes) -> str:
    """Extract plain text from a DOCX file supplied as raw bytes.

    Reads all paragraph text, skipping paragraphs that are empty or
    whitespace-only, and joins non-empty paragraphs with newlines. Returns
    an empty string if the bytes are not a valid DOCX, if python-docx is not
    installed, or if no text can be extracted.

    Args:
        content_bytes: Raw bytes of a DOCX file.

    Returns:
        Extracted text, or ``""`` on any error.
    """
    try:
        from docx import Document  # noqa: PLC0415
    except ImportError:
        return ""

    try:
        doc = Document(io.BytesIO(content_bytes))
        lines = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(lines)
    except Exception:
        return ""


def extract_resume_text(
    content_base64: str,
    content_type: str,
    filename: str = "",
) -> str:
    """Decode and extract plain text from a base64-encoded resume attachment.

    Detects the file format from ``content_type`` first, falling back to the
    ``filename`` extension. Dispatches to the appropriate extractor:

    - PDF:  ``content_type == "application/pdf"`` or filename ends with ``.pdf``
    - DOCX: content_type is one of the Word MIME types, or filename ends with
      ``.docx`` / ``.doc``
    - Unknown: attempts a UTF-8 decode (plain-text resume); returns ``""`` if
      the bytes are not valid UTF-8.

    Args:
        content_base64: Base64-encoded file content (as returned by the
            Greenhouse ``download_url`` helper).
        content_type: MIME type string for the attachment.
        filename: Optional original filename; used for extension-based
            detection when content_type is ambiguous.

    Returns:
        Extracted plain text, or ``""`` if the content cannot be parsed.
    """
    try:
        content_bytes = base64.b64decode(content_base64)
    except Exception:
        return ""

    lower_filename = filename.lower()

    _PDF_CONTENT_TYPE = "application/pdf"
    _DOCX_CONTENT_TYPES = frozenset(
        {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        }
    )

    is_pdf = content_type == _PDF_CONTENT_TYPE or lower_filename.endswith(".pdf")
    is_docx = content_type in _DOCX_CONTENT_TYPES or lower_filename.endswith(
        (".docx", ".doc")
    )

    if is_pdf:
        return extract_text_from_pdf(content_bytes)

    if is_docx:
        return extract_text_from_docx(content_bytes)

    # Fallback: attempt UTF-8 plain-text decode
    try:
        return content_bytes.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return ""
