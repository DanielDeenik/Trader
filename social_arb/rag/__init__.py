"""RAG layer (NB-003) — cited generation over notebook-scoped sources."""
from social_arb.rag.cited_generator import (
    Citation,
    CitedAnswer,
    CitedGenerator,
    parse_citations,
    strip_hallucinated,
    validate_citations,
)
from social_arb.rag.llm import (
    ClaudeLLM,
    EchoLLM,
    LLMMessage,
    LLMProtocol,
    LLMRequest,
    LLMResponse,
    create_llm,
)
from social_arb.rag.retriever import RetrievalResult, RetrievedChunk, Retriever

__all__ = [
    "Citation",
    "CitedAnswer",
    "CitedGenerator",
    "ClaudeLLM",
    "EchoLLM",
    "LLMMessage",
    "LLMProtocol",
    "LLMRequest",
    "LLMResponse",
    "RetrievalResult",
    "RetrievedChunk",
    "Retriever",
    "create_llm",
    "parse_citations",
    "strip_hallucinated",
    "validate_citations",
]
