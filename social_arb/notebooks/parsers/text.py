"""Plain-text + pasted-text parsers."""
from __future__ import annotations

from social_arb.notebooks.parsers.base import ContentHint, ParsedSource, ParserProtocol
from social_arb.sources.models import SourceKind


class TextParser(ParserProtocol):
    kind = SourceKind.TEXT

    def can_parse(self, hint: ContentHint) -> bool:
        if hint.content_type and hint.content_type.startswith("text/plain"):
            return True
        if hint.filename and hint.filename.lower().endswith((".txt", ".md", ".rst")):
            return True
        return False

    def parse(self, blob: bytes | str, hint: ContentHint) -> ParsedSource:
        text = blob.decode("utf-8", errors="replace") if isinstance(blob, bytes) else blob
        title = hint.title_hint or hint.filename or "Untitled text"
        return ParsedSource(
            text=text,
            title=title,
            kind=self.kind,
            uri=hint.uri,
            metadata={"length": len(text), "lines": text.count("\n") + 1},
        )


class PastedTextParser(ParserProtocol):
    """Pasted-into-textarea text. Same handler as TextParser but kind=PASTED."""

    kind = SourceKind.PASTED

    def can_parse(self, hint: ContentHint) -> bool:
        # Dispatcher uses this when the source originates from a paste action.
        return hint.extra.get("source_kind") == "paste"

    def parse(self, blob: bytes | str, hint: ContentHint) -> ParsedSource:
        text = blob.decode("utf-8", errors="replace") if isinstance(blob, bytes) else blob
        title = hint.title_hint or "Pasted text"
        return ParsedSource(
            text=text,
            title=title,
            kind=self.kind,
            uri=None,
            metadata={"length": len(text)},
        )
