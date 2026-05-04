"""Tests for parsers (text, pasted, url) + dispatch.

PDF + DOCX parsers tested separately so they can be skipped when the
optional deps aren't installed.
"""
import pytest

from social_arb.notebooks.parsers import (
    ContentHint,
    PastedTextParser,
    TextParser,
    UrlParser,
    dispatch_parser,
    parse_blob,
)


# --- TextParser ------------------------------------------------------------ #

def test_text_parser_claims_txt_files():
    p = TextParser()
    assert p.can_parse(ContentHint(filename="notes.txt"))
    assert p.can_parse(ContentHint(content_type="text/plain"))
    assert not p.can_parse(ContentHint(filename="report.pdf"))


def test_text_parser_round_trips_string():
    p = TextParser()
    parsed = p.parse("hello world", ContentHint(filename="memo.txt"))
    assert parsed.text == "hello world"
    assert parsed.title == "memo.txt"
    assert parsed.metadata["length"] == 11


def test_text_parser_decodes_bytes():
    p = TextParser()
    parsed = p.parse(b"hello", ContentHint(filename="memo.txt"))
    assert parsed.text == "hello"


# --- PastedTextParser ------------------------------------------------------ #

def test_pasted_text_parser_uses_extra_hint():
    p = PastedTextParser()
    hint = ContentHint(extra={"source_kind": "paste"})
    assert p.can_parse(hint)
    parsed = p.parse("clipboard content", hint)
    assert parsed.title == "Pasted text"
    assert parsed.kind.value == "pasted"


# --- UrlParser ------------------------------------------------------------- #

def test_url_parser_claims_http_uris():
    p = UrlParser()
    assert p.can_parse(ContentHint(uri="https://example.com"))
    assert p.can_parse(ContentHint(content_type="text/html"))
    assert not p.can_parse(ContentHint(uri="file:///tmp/x.txt"))


def test_url_parser_strips_scripts_and_styles():
    p = UrlParser()
    html = (
        "<html><head><title>Hello</title>"
        "<style>body{color:red}</style></head>"
        "<body><script>x=1</script>"
        "<h1>Heading</h1><p>Body text.</p></body></html>"
    )
    parsed = p.parse(html, ContentHint(uri="https://example.com"))
    assert "Body text" in parsed.text
    assert "color:red" not in parsed.text
    assert "x=1" not in parsed.text
    # Title should come from <title>.
    assert parsed.title == "Hello"


# --- Dispatch -------------------------------------------------------------- #

def test_dispatch_picks_url_for_https():
    parser = dispatch_parser(ContentHint(uri="https://example.com"))
    assert isinstance(parser, UrlParser)


def test_dispatch_picks_text_for_txt():
    parser = dispatch_parser(ContentHint(filename="x.txt"))
    assert isinstance(parser, TextParser)


def test_dispatch_picks_pasted_for_paste_hint():
    parser = dispatch_parser(ContentHint(extra={"source_kind": "paste"}))
    assert isinstance(parser, PastedTextParser)


def test_dispatch_raises_on_unmatched():
    with pytest.raises(ValueError, match="No parser matched"):
        dispatch_parser(ContentHint(content_type="application/octet-stream"))


def test_parse_blob_convenience():
    parsed = parse_blob("plain text", ContentHint(filename="x.txt"))
    assert parsed.text == "plain text"
