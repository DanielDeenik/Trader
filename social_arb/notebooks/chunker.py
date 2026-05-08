"""Token-aware chunker.

Splits ParsedSource.text into overlapping chunks suitable for embedding.
Token counting uses tiktoken when available, falls back to whitespace
word count (which is a reasonable approximation for English).

Chunks are deterministic: same input ⇒ same chunk_id sequence.
"""
from __future__ import annotations

from dataclasses import dataclass

from social_arb.notebooks.parsers.base import ParsedSource
from social_arb.sources.models import (
    Source,
    SourceChunk,
    make_chunk_id,
    make_source_id,
)


@dataclass
class ChunkerConfig:
    chunk_size_tokens: int = 400
    chunk_overlap_tokens: int = 60
    min_chunk_tokens: int = 30  # drop tail chunks shorter than this


def _count_tokens(text: str) -> int:
    """Best-effort token count. Uses tiktoken if available."""
    try:
        import tiktoken  # type: ignore
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        # Fallback: whitespace word count.
        return len(text.split())


def _tokenize(text: str) -> list[str]:
    """Best-effort tokenization. Returns string tokens whose join yields text."""
    try:
        import tiktoken  # type: ignore
        enc = tiktoken.get_encoding("cl100k_base")
        ids = enc.encode(text)
        return [enc.decode([tid]) for tid in ids]
    except ImportError:
        # Fallback: split on whitespace, preserving as words. Re-join with " ".
        return text.split()


def _detokenize(tokens: list[str]) -> str:
    try:
        import tiktoken  # type: ignore  # noqa: F401
        return "".join(tokens)
    except ImportError:
        return " ".join(tokens)


class Chunker:
    def __init__(self, config: ChunkerConfig | None = None) -> None:
        self.config = config or ChunkerConfig()

    def chunk(self, parsed: ParsedSource) -> tuple[Source, list[SourceChunk]]:
        """Convert a ParsedSource to a Source + its SourceChunks."""
        source_id = make_source_id(parsed.text, parsed.kind, parsed.uri)
        source = Source.build(
            text=parsed.text,
            kind=parsed.kind,
            title=parsed.title,
            uri=parsed.uri,
            metadata=parsed.metadata,
        )

        tokens = _tokenize(parsed.text)
        size = self.config.chunk_size_tokens
        overlap = self.config.chunk_overlap_tokens
        step = max(1, size - overlap)

        chunks: list[SourceChunk] = []
        char_cursor = 0
        for index, start in enumerate(range(0, len(tokens), step)):
            window = tokens[start : start + size]
            if len(window) < self.config.min_chunk_tokens and chunks:
                break
            chunk_text = _detokenize(window)
            char_start = char_cursor
            char_end = char_start + len(chunk_text)
            char_cursor = char_end
            chunks.append(
                SourceChunk(
                    id=make_chunk_id(source_id, index, chunk_text),
                    source_id=source_id,
                    chunk_index=index,
                    text=chunk_text,
                    char_start=char_start,
                    char_end=char_end,
                    metadata={"token_count": len(window)},
                )
            )

        source = source.model_copy(update={"chunk_count": len(chunks)})
        return source, chunks
