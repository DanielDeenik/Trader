"""URL parser — fetch + readability extraction.

Uses httpx for the fetch and BeautifulSoup for tag-strip extraction.
For higher-quality extraction, swap to readability-lxml or trafilatura
in a future ticket; the interface stays the same.
"""
from __future__ import annotations

from social_arb.notebooks.parsers.base import ContentHint, ParsedSource, ParserProtocol
from social_arb.sources.models import SourceKind


class UrlParser(ParserProtocol):
    kind = SourceKind.URL

    def can_parse(self, hint: ContentHint) -> bool:
        if hint.uri and hint.uri.startswith(("http://", "https://")):
            return True
        if hint.content_type and hint.content_type.startswith("text/html"):
            return True
        return False

    def parse(self, blob: bytes | str, hint: ContentHint) -> ParsedSource:
        # Two modes:
        #   1) blob is HTML bytes/str (already fetched)
        #   2) blob is empty/missing — fetch from hint.uri
        if not blob and hint.uri:
            try:
                import httpx  # type: ignore
            except ImportError as e:
                raise ImportError(
                    "httpx not installed — `pip install httpx`"
                ) from e
            r = httpx.get(hint.uri, timeout=15.0, follow_redirects=True)
            r.raise_for_status()
            html = r.text
            content_type = r.headers.get("content-type")
        else:
            html = blob.decode("utf-8", errors="replace") if isinstance(blob, bytes) else blob
            content_type = hint.content_type

        try:
            from bs4 import BeautifulSoup  # type: ignore
        except ImportError as e:
            raise ImportError(
                "beautifulsoup4 not installed — `pip install beautifulsoup4`"
            ) from e

        soup = BeautifulSoup(html, "html.parser")
        # Remove obvious non-content noise.
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            tag.decompose()

        # Title from <title> or <h1>.
        page_title = (soup.title.string.strip() if soup.title and soup.title.string else None) or (
            soup.h1.get_text(strip=True) if soup.h1 else None
        )
        text = soup.get_text(separator="\n", strip=True)
        title = hint.title_hint or page_title or hint.uri or "Untitled web page"

        return ParsedSource(
            text=text,
            title=title,
            kind=self.kind,
            uri=hint.uri,
            metadata={
                "content_type": content_type,
                "char_count": len(text),
            },
        )
