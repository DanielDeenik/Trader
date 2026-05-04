"""DOCX parser test — skipped if python-docx isn't installed."""
import io

import pytest

docx = pytest.importorskip("docx")  # python-docx imports as `docx`

from social_arb.notebooks.parsers import ContentHint, DocxParser


def _make_minimal_docx(paragraphs: list[str]) -> bytes:
    document = docx.Document()
    for p in paragraphs:
        document.add_paragraph(p)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def test_docx_parser_claims_docx_files():
    p = DocxParser()
    assert p.can_parse(ContentHint(filename="notes.docx"))
    assert p.can_parse(
        ContentHint(content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    )


def test_docx_parser_extracts_paragraphs():
    p = DocxParser()
    blob = _make_minimal_docx(["First paragraph.", "Second paragraph."])
    parsed = p.parse(blob, ContentHint(filename="notes.docx"))
    assert "First paragraph" in parsed.text
    assert "Second paragraph" in parsed.text
    assert parsed.metadata["paragraph_count"] == 2
