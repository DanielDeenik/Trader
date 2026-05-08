"""Dispatcher — picks a ParserProtocol implementation by sniffing the hint."""
from __future__ import annotations

from social_arb.notebooks.parsers.base import ContentHint, ParsedSource, ParserProtocol
from social_arb.notebooks.parsers.docx import DocxParser
from social_arb.notebooks.parsers.pdf import PdfParser
from social_arb.notebooks.parsers.text import PastedTextParser, TextParser
from social_arb.notebooks.parsers.url import UrlParser

# Order matters: more specific first.
_DEFAULT_PARSERS: list[ParserProtocol] = [
    PastedTextParser(),
    PdfParser(),
    DocxParser(),
    UrlParser(),
    TextParser(),  # fallback for any text/* content
]


def dispatch_parser(hint: ContentHint, parsers: list[ParserProtocol] | None = None) -> ParserProtocol:
    """Return the first parser that claims the hint.

    Raises ValueError if no parser matches (caller decides whether to fall
    back to the LLM multimodal route, which lives outside NB-001).
    """
    pool = parsers if parsers is not None else _DEFAULT_PARSERS
    for parser in pool:
        if parser.can_parse(hint):
            return parser
    raise ValueError(
        f"No parser matched hint: content_type={hint.content_type!r} "
        f"filename={hint.filename!r} uri={hint.uri!r}"
    )


def parse_blob(
    blob: bytes | str,
    hint: ContentHint,
    parsers: list[ParserProtocol] | None = None,
) -> ParsedSource:
    """Convenience: dispatch + parse in one call."""
    parser = dispatch_parser(hint, parsers)
    return parser.parse(blob, hint)
