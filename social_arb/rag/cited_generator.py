"""Cited RAG generation (NB-003).

Workflow:
  query  ─►  Retriever ─► chunks ─► PromptBuilder ─► LLM
                                                       │
                                  CitationValidator ◄──┘
                                          │
                                   {answer, valid, hallucinated}

Hallucinated citations (chunk IDs the LLM made up) are STRIPPED from
the final answer text and listed separately so callers / UI can flag
them. Per DLOG-15, citation tokens are `[s:<source_id>:<chunk_id>]`.
"""
from __future__ import annotations

import re
from typing import Sequence

from pydantic import BaseModel, Field

from social_arb.rag.llm import LLMMessage, LLMProtocol, LLMRequest
from social_arb.rag.retriever import RetrievedChunk, Retriever, RetrievalResult


CITATION_RE = re.compile(r"\[s:([A-Za-z0-9_\-:]+):([A-Za-z0-9_\-]+)\]")


class Citation(BaseModel):
    source_id: str
    chunk_id: str

    @property
    def token(self) -> str:
        return f"[s:{self.source_id}:{self.chunk_id}]"


class CitedAnswer(BaseModel):
    notebook_id: str
    query: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    hallucinated: list[Citation] = Field(default_factory=list)
    retrieval: RetrievalResult
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


_SYSTEM_PROMPT = """You are a research assistant for the Social Arb information-arbitrage platform.
You answer questions by drawing ONLY on the sources provided in the user message.
Every factual claim MUST be followed by a citation token of the form
[s:<source_id>:<chunk_id>] referencing one of the chunks shown.
Never invent citation tokens. If the sources do not support an answer, say so plainly.
Keep answers concise: prefer 2-4 short paragraphs over long prose.""".strip()


def parse_citations(text: str) -> list[Citation]:
    """Extract every `[s:sid:cid]` token from the text in order."""
    return [
        Citation(source_id=sid, chunk_id=cid)
        for sid, cid in CITATION_RE.findall(text)
    ]


def validate_citations(
    citations: Sequence[Citation],
    retrieved: Sequence[RetrievedChunk],
) -> tuple[list[Citation], list[Citation]]:
    """Split citations into (valid, hallucinated) given the retrieval set."""
    allowed: set[tuple[str, str]] = {
        (rc.chunk.source_id, rc.chunk.id) for rc in retrieved
    }
    valid: list[Citation] = []
    hallucinated: list[Citation] = []
    for c in citations:
        (valid if (c.source_id, c.chunk_id) in allowed else hallucinated).append(c)
    return valid, hallucinated


def strip_hallucinated(text: str, hallucinated: Sequence[Citation]) -> str:
    """Remove hallucinated citation tokens from the answer text.

    Applied AFTER validation so the user never sees a fake citation
    that resolves to nothing on hover (NB-005's hover-quote rendering
    would 404 otherwise).
    """
    if not hallucinated:
        return text
    out = text
    for c in hallucinated:
        out = out.replace(c.token, "")
    return re.sub(r"\s{2,}", " ", out).strip()


def _format_chunks_for_prompt(retrieved: Sequence[RetrievedChunk]) -> str:
    parts: list[str] = []
    for rc in retrieved:
        parts.append(
            f"<source source_id={rc.chunk.source_id!r} chunk_id={rc.chunk.id!r} score={rc.score:.4f}>\n"
            f"{rc.chunk.text}\n"
            f"</source>"
        )
    return "\n\n".join(parts)


class CitedGenerator:
    def __init__(self, llm: LLMProtocol, retriever: Retriever) -> None:
        self._llm = llm
        self._retriever = retriever

    def generate(
        self,
        notebook_id: str,
        query: str,
        *,
        k: int = 8,
        max_tokens: int = 1024,
    ) -> CitedAnswer:
        retrieval = self._retriever.retrieve(notebook_id, query, k=k)

        if not retrieval.chunks:
            # No sources attached or no hits — degrade gracefully.
            return CitedAnswer(
                notebook_id=notebook_id,
                query=query,
                answer="No sources are attached to this notebook yet, so I cannot ground an answer. Add sources first.",
                retrieval=retrieval,
                model="none",
            )

        chunk_block = _format_chunks_for_prompt(retrieval.chunks)
        user_prompt = (
            f"Question:\n{query}\n\n"
            f"Sources (cite using [s:source_id:chunk_id]):\n{chunk_block}"
        )

        response = self._llm.complete(
            LLMRequest(
                messages=[
                    LLMMessage(role="system", content=_SYSTEM_PROMPT),
                    LLMMessage(role="user", content=user_prompt),
                ],
                max_tokens=max_tokens,
            )
        )

        all_citations = parse_citations(response.text)
        valid, hallucinated = validate_citations(all_citations, retrieval.chunks)
        clean_answer = strip_hallucinated(response.text, hallucinated)

        return CitedAnswer(
            notebook_id=notebook_id,
            query=query,
            answer=clean_answer,
            citations=valid,
            hallucinated=hallucinated,
            retrieval=retrieval,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
