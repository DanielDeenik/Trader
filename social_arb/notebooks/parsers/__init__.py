"""Parsers — multi-format source ingestion (NB-001 / DLOG-17).

Every parser implements ParserProtocol. Dispatch picks one by content
sniffing. New formats plug in without touching the core.
"""
from social_arb.notebooks.parsers.base import (
    ContentHint,
    ParsedSource,
    ParserProtocol,
)
from social_arb.notebooks.parsers.dispatch import dispatch_parser, parse_blob
from social_arb.notebooks.parsers.docx import DocxParser
from social_arb.notebooks.parsers.pdf import PdfParser
from social_arb.notebooks.parsers.text import PastedTextParser, TextParser
from social_arb.notebooks.parsers.url import UrlParser

__all__ = [
    "ContentHint",
    "ParsedSource",
    "ParserProtocol",
    "TextParser",
    "PastedTextParser",
    "PdfParser",
    "DocxParser",
    "UrlParser",
    "dispatch_parser",
    "parse_blob",
]
