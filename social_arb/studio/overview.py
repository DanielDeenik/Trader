"""Overview generator (NB-004) — one-page brief in Markdown.

Reuses NB-003's CitedGenerator (retrieval + cited LLM call) and wraps
it with a structured prompt that asks for four sections:

  ## Thesis
  ## Catalysts
  ## Risks
  ## Recent signals

The output Artifact's `content` shape:

    {
      "markdown": "<full text including citations>",
      "sections": {"thesis": str, "catalysts": str, "risks": str, "recent_signals": str},
    }

`sections` is best-effort parsed from the markdown so the frontend can
render each section independently. If parsing fails (model deviated
from the template), `sections` falls back to {"_full": markdown}.
"""
from __future__ import annotations

import re
from typing import Any

from social_arb.notebooks.notebook_models import ArtifactKind
from social_arb.rag import (
    Citation,
    CitedGenerator,
    LLMProtocol,
    Retriever,
)


OVERVIEW_PROMPT = """Produce a one-page brief on this notebook in Markdown.
Use EXACTLY these four section headers in this order:

## Thesis
## Catalysts
## Risks
## Recent signals

Each section: 2-4 short sentences. Every factual claim MUST be followed by a
citation token of the form [s:<source_id>:<chunk_id>] referencing one of the
chunks shown. If a section has nothing to say, write "No material findings" —
do not invent content.""".strip()


# Forgiving section parser — accepts ##, ###, ** **, and bare lines.
_SECTION_RE = re.compile(
    r"(?:^|\n)(?:#{1,4}\s+|\*\*)?(Thesis|Catalysts|Risks|Recent\s+signals)"
    r"\s*(?:\*\*)?\s*:?\s*\n+(.*?)(?=\n(?:#{1,4}\s+|\*\*)?(?:Thesis|Catalysts|Risks|Recent\s+signals)\b|\Z)",
    re.DOTALL | re.IGNORECASE,
)


def parse_sections(markdown: str) -> dict[str, str]:
    """Best-effort split of a four-section brief into a dict."""
    sections: dict[str, str] = {}
    for match in _SECTION_RE.finditer(markdown):
        header = match.group(1).strip().lower().replace(" ", "_")
        body = match.group(2).strip()
        sections[header] = body
    return sections


class OverviewGenerator:
    """Wraps CitedGenerator with the overview prompt."""

    kind = ArtifactKind.OVERVIEW
    version = "v0"

    def build(
        self,
        notebook_id: str,
        params: dict[str, Any],
        *,
        retriever: Retriever,
        llm: LLMProtocol,
    ) -> tuple[dict[str, Any], list[Citation]]:
        generator = CitedGenerator(llm, retriever)
        k = int(params.get("max_chunks", 12))
        max_tokens = int(params.get("max_tokens", 1500))

        answer = generator.generate(
            notebook_id,
            OVERVIEW_PROMPT,
            k=k,
            max_tokens=max_tokens,
        )

        sections = parse_sections(answer.answer)
        if not sections:
            sections = {"_full": answer.answer}

        content = {
            "markdown": answer.answer,
            "sections": sections,
            "hallucinated": [c.token for c in answer.hallucinated],
            "model": answer.model,
            "retrieval_ms": answer.retrieval.elapsed_ms,
        }
        return content, answer.citations
