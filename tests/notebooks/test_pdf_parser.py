"""PDF parser test — skipped if pdfplumber isn't installed."""
import io

import pytest

pdfplumber = pytest.importorskip("pdfplumber")
reportlab = pytest.importorskip("reportlab")

from social_arb.notebooks.parsers import ContentHint, PdfParser


def _make_minimal_pdf(text: str = "Hello PDF") -> bytes:
    """Build a minimal one-page PDF with the given text."""
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, text)
    c.showPage()
    c.save()
    return buf.getvalue()


def test_pdf_parser_claims_pdf_files():
    p = PdfParser()
    assert p.can_parse(ContentHint(filename="report.pdf"))
    assert p.can_parse(ContentHint(content_type="application/pdf"))
    assert not p.can_parse(ContentHint(filename="notes.txt"))


def test_pdf_parser_extracts_text():
    p = PdfParser()
    blob = _make_minimal_pdf("AMD Q1 thesis: divergence 70.4")
    parsed = p.parse(blob, ContentHint(filename="amd-q1.pdf"))
    assert "AMD Q1" in parsed.text
    assert parsed.metadata["page_count"] == 1
    assert parsed.title == "amd-q1.pdf"


def test_pdf_parser_rejects_str():
    p = PdfParser()
    with pytest.raises(TypeError):
        p.parse("not bytes", ContentHint(filename="x.pdf"))
