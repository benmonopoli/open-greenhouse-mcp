"""Tests for greenhouse_mcp.resume_parser — PDF, DOCX, and dispatcher coverage."""
from __future__ import annotations

import base64
import io

from docx import Document
from fpdf import FPDF

from greenhouse_mcp.resume_parser import (
    extract_resume_text,
    extract_text_from_docx,
    extract_text_from_pdf,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pdf_bytes(pages: list[str]) -> bytes:
    """Generate a real PDF with given text on successive pages."""
    pdf = FPDF()
    for page_text in pages:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 10, page_text)
    return pdf.output()


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    """Generate a real DOCX with given paragraphs, including any empty strings."""
    doc = Document()
    for para in paragraphs:
        doc.add_paragraph(para)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


# ---------------------------------------------------------------------------
# extract_text_from_pdf
# ---------------------------------------------------------------------------


class TestExtractTextFromPdf:
    def test_simple_text(self):
        pdf_bytes = _make_pdf_bytes(["Hello World"])
        result = extract_text_from_pdf(pdf_bytes)
        assert "Hello" in result
        assert "World" in result

    def test_multipage(self):
        pdf_bytes = _make_pdf_bytes(["Page one content", "Page two content"])
        result = extract_text_from_pdf(pdf_bytes)
        assert "Page one" in result
        assert "Page two" in result

    def test_empty_pdf_returns_empty_string(self):
        # A PDF with a page but no drawn text — pdfplumber extracts nothing
        pdf = FPDF()
        pdf.add_page()
        pdf_bytes = pdf.output()
        result = extract_text_from_pdf(pdf_bytes)
        assert result == ""

    def test_invalid_bytes_returns_empty_string(self):
        result = extract_text_from_pdf(b"this is not a pdf")
        assert result == ""


# ---------------------------------------------------------------------------
# extract_text_from_docx
# ---------------------------------------------------------------------------


class TestExtractTextFromDocx:
    def test_simple_text(self):
        docx_bytes = _make_docx_bytes(["Alice Smith", "Python Engineer"])
        result = extract_text_from_docx(docx_bytes)
        assert "Alice Smith" in result
        assert "Python Engineer" in result

    def test_skips_empty_paragraphs(self):
        docx_bytes = _make_docx_bytes(["First", "", "Third"])
        result = extract_text_from_docx(docx_bytes)
        lines = result.splitlines()
        # No empty lines should appear
        assert "" not in lines
        assert "First" in result
        assert "Third" in result

    def test_invalid_bytes_returns_empty_string(self):
        result = extract_text_from_docx(b"not a docx file at all")
        assert result == ""


# ---------------------------------------------------------------------------
# extract_resume_text (dispatcher)
# ---------------------------------------------------------------------------


class TestExtractResumeText:
    def test_routes_by_pdf_content_type(self):
        pdf_bytes = _make_pdf_bytes(["Dispatcher PDF test"])
        result = extract_resume_text(_b64(pdf_bytes), "application/pdf")
        assert "Dispatcher PDF test" in result

    def test_routes_by_pdf_filename_extension(self):
        pdf_bytes = _make_pdf_bytes(["Filename routing PDF"])
        result = extract_resume_text(
            _b64(pdf_bytes), "application/octet-stream", filename="resume.pdf"
        )
        assert "Filename routing PDF" in result

    def test_routes_by_docx_content_type(self):
        docx_bytes = _make_docx_bytes(["Dispatcher DOCX test"])
        result = extract_resume_text(
            _b64(docx_bytes),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        assert "Dispatcher DOCX test" in result

    def test_routes_by_msword_content_type(self):
        # application/msword maps to the DOCX extractor; if bytes happen to be
        # a valid DOCX we should get text back (modern .doc saved as docx)
        docx_bytes = _make_docx_bytes(["MSWord content type"])
        result = extract_resume_text(
            _b64(docx_bytes), "application/msword"
        )
        assert "MSWord content type" in result

    def test_routes_by_docx_filename_extension(self):
        docx_bytes = _make_docx_bytes(["DOCX filename ext"])
        result = extract_resume_text(
            _b64(docx_bytes), "application/octet-stream", filename="cv.docx"
        )
        assert "DOCX filename ext" in result

    def test_routes_by_doc_filename_extension(self):
        docx_bytes = _make_docx_bytes(["DOC filename ext"])
        result = extract_resume_text(
            _b64(docx_bytes), "application/octet-stream", filename="resume.doc"
        )
        assert "DOC filename ext" in result

    def test_text_fallback_for_unknown_type(self):
        plain = "Just plain text resume content"
        result = extract_resume_text(_b64(plain.encode()), "text/plain")
        assert "plain text resume" in result

    def test_unknown_binary_returns_empty_string(self):
        garbage = bytes(range(256)) * 4  # arbitrary binary, not valid text
        result = extract_resume_text(_b64(garbage), "application/octet-stream")
        assert result == ""

    def test_content_type_takes_priority_over_extension(self):
        """application/pdf content_type should win even if filename says .docx."""
        pdf_bytes = _make_pdf_bytes(["Priority test"])
        result = extract_resume_text(
            _b64(pdf_bytes), "application/pdf", filename="tricky.docx"
        )
        assert "Priority test" in result
