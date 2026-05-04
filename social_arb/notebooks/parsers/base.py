"""ParserProtocol contract (NB-001 / DLOG-17).

Every parser exposes a single method `parse(blob, hint) -> ParsedSource`.
A `ContentHint` carries content-type guesses, original filename, and
URI so parsers can disambiguate (e.g. "this is .docx vs .doc").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from social_arb.sources.models import SourceKind


@dataclass
class ContentHint:
    """What the dispatcher knows about the blob before any parser runs."""

    content_type: str | None = None    # e.g. "application/pdf"
    filename: str | None = None        # e.g. "report.pdf"
    uri: str | None = None             # original URL or upload path
    title_hint: str | None = None      # if the user gave one
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedSource:
    """The parser's output. The chunker takes it from here."""

    text: str
    title: str
    kind: SourceKind
    uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ParserProtocol(Protocol):
    """A parser converts a blob into a ParsedSource."""

    kind: SourceKind

    def can_parse(self, hint: ContentHint) -> bool:
        """Return True if this parser claims responsibility for the blob."""
        ...

    def parse(self, blob: bytes | str, hint: ContentHint) -> ParsedSource:
        """Convert blob+hint to ParsedSource. May raise on malformed input."""
        ...
