"""PDF parser via pdfplumber.

Falls back gracefully if pdfplumber isn't installed — raises a clear
ImportError pointing at the install command. Lets the rest of the
package import without the optional dep.
"""
from __future__ import annotations

from social_arb.notebooks.parsers.base import ContentHint, ParsedSource, ParserProtocol
from social_arb.sources.models import SourceKind


class PdfParser(ParserProtocol):
    kind = SourceKind.PDF

    def can_parse(self, hint: ContentHint) -> bool:
        if hint.content_type == "application/pdf":
            return True
        if hint.filename and hint.filename.lower().endswith(".pdf"):
            return True
        return False

    def parse(self, blob: bytes | str, hint: ContentHint) -> ParsedSource:
        if isinstance(blob, str):
            raise TypeError("PdfParser requires bytes, got str")
        try:
            import pdfplumber  # type: ignore
        except ImportError as e:
            raise ImportError(
                "pdfplumber not installed — `pip install pdfplumber`"
            ) from e

        import io

        text_parts: list[str] = []
        page_count = 0
        with pdfplumber.open(io.BytesIO(blob)) as pdf:
            for page in pdf.pages:
                page_count += 1
                page_text = page.extract_text() or ""
                if page_text:
                    text_parts.append(page_text)

        text = "\n\n".join(text_parts)
        title = hint.title_hint or hint.filename or "Untitled PDF"

        return ParsedSource(
            text=text,
            title=title,
            kind=self.kind,
            uri=hint.uri,
            metadata={
                "page_count": page_count,
                "char_count": len(text),
            },
        )
