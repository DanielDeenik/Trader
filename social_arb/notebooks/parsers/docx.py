"""DOCX parser via python-docx."""
from __future__ import annotations

from social_arb.notebooks.parsers.base import ContentHint, ParsedSource, ParserProtocol
from social_arb.sources.models import SourceKind


class DocxParser(ParserProtocol):
    kind = SourceKind.DOCX

    def can_parse(self, hint: ContentHint) -> bool:
        ct = hint.content_type or ""
        if "wordprocessingml" in ct or ct == "application/msword":
            return True
        if hint.filename and hint.filename.lower().endswith(".docx"):
            return True
        return False

    def parse(self, blob: bytes | str, hint: ContentHint) -> ParsedSource:
        if isinstance(blob, str):
            raise TypeError("DocxParser requires bytes, got str")
        try:
            import docx  # type: ignore  # python-docx
        except ImportError as e:
            raise ImportError(
                "python-docx not installed — `pip install python-docx`"
            ) from e

        import io

        document = docx.Document(io.BytesIO(blob))
        paragraphs = [p.text for p in document.paragraphs if p.text]
        text = "\n\n".join(paragraphs)
        title = hint.title_hint or hint.filename or "Untitled DOCX"

        return ParsedSource(
            text=text,
            title=title,
            kind=self.kind,
            uri=hint.uri,
            metadata={
                "paragraph_count": len(paragraphs),
                "char_count": len(text),
            },
        )
