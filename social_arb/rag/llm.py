"""LLM provider abstraction (NB-003).

`LLMProtocol` lets the rest of RAG be agnostic to the model vendor.
Production = Anthropic Claude (DLOG-20). Tests use `EchoLLM` to make
generation deterministic without burning real tokens.

Adding a new provider = implement the protocol; nothing else changes.
"""
from __future__ import annotations

import os
import re
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMRequest(BaseModel):
    messages: list[LLMMessage]
    max_tokens: int = 1024
    temperature: float = 0.0   # deterministic by default for citation work


class LLMResponse(BaseModel):
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str | None = None


@runtime_checkable
class LLMProtocol(Protocol):
    """Anything that can take an LLMRequest and return an LLMResponse."""

    def complete(self, request: LLMRequest) -> LLMResponse: ...


class ClaudeLLM:
    """Anthropic Claude implementation (DLOG-20).

    Lazy-imports the SDK so tests don't pull it in. Reads
    `ANTHROPIC_API_KEY` from the environment by default.
    """

    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-5",
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None  # lazy

    def _ensure_client(self):
        if self._client is None:
            try:
                import anthropic  # type: ignore
            except ImportError as e:
                raise RuntimeError(
                    "Anthropic SDK not installed. `pip install anthropic`."
                ) from e
            if not self._api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY missing. Set the env var or pass api_key= explicitly."
                )
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def complete(self, request: LLMRequest) -> LLMResponse:
        client = self._ensure_client()
        # Split system/user — Anthropic's Messages API takes system as a
        # top-level param, everything else as messages.
        system_parts = [m.content for m in request.messages if m.role == "system"]
        chat_messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role != "system"
        ]
        result = client.messages.create(
            model=self.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system="\n\n".join(system_parts) if system_parts else "",
            messages=chat_messages,
        )
        text = "".join(
            block.text for block in result.content if getattr(block, "type", "") == "text"
        )
        return LLMResponse(
            text=text,
            model=self.model,
            input_tokens=getattr(result.usage, "input_tokens", 0),
            output_tokens=getattr(result.usage, "output_tokens", 0),
            stop_reason=getattr(result, "stop_reason", None),
        )


class EchoLLM:
    """Deterministic test fixture: returns a fixed answer plus citations.

    Configure with `answer_template` (uses `{chunk_count}`) and
    `cite_chunks` (list of (source_id, chunk_id) tuples to emit). The
    output looks like real cited prose so the citation parser /
    validator can be exercised without a real LLM.
    """

    def __init__(
        self,
        answer_template: str = "Based on {chunk_count} retrieved chunks, here is the answer.",
        cite_chunks: list[tuple[str, str]] | None = None,
        model_name: str = "echo-test-v1",
    ) -> None:
        self.answer_template = answer_template
        self.cite_chunks = cite_chunks or []
        self._model_name = model_name

    def complete(self, request: LLMRequest) -> LLMResponse:
        # Count the chunk markers in the user prompt — robust signal
        # that the prompt is wired correctly.
        user_prompt = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "",
        )
        chunk_count = len(re.findall(r"<source[^>]+chunk_id=", user_prompt))
        # Only apply str.format if the template explicitly opts in via the
        # `{chunk_count}` placeholder. Avoids KeyError on templates that
        # contain unrelated braces (e.g. JSON for Mind Map output).
        if "{chunk_count}" in self.answer_template:
            body = self.answer_template.format(chunk_count=chunk_count)
        else:
            body = self.answer_template
        citations = " ".join(f"[s:{sid}:{cid}]" for sid, cid in self.cite_chunks)
        text = f"{body} {citations}".strip()
        return LLMResponse(
            text=text,
            model=self._model_name,
            input_tokens=len(user_prompt) // 4,
            output_tokens=len(text) // 4,
        )


def create_llm(provider: str | None = None) -> LLMProtocol:
    """Factory used by the API DI hook. Defaults to Claude when configured,
    falls back to EchoLLM (so tests/local-dev work without an API key)."""
    provider = provider or os.environ.get("SOCIAL_ARB_LLM", "auto")
    if provider == "claude" or (provider == "auto" and os.environ.get("ANTHROPIC_API_KEY")):
        return ClaudeLLM()
    return EchoLLM()
