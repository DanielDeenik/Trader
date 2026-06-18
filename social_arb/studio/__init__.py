"""Studio (NB-004) — composable generators that turn a Notebook + Sources
into frozen, cited Artifacts. Each generator is a pure function of
(notebook, params, retriever, llm) per DLOG-19.

Initial kinds shipped in v0: Overview (Markdown brief), Mind Map
(Cytoscape JSON). Audio / Slide deck / Reports / Flashcards / Quiz /
Data table are NB-008+ follow-ups.
"""
from social_arb.notebooks.notebook_models import ArtifactKind
from social_arb.notebooks.notebook_store import NotebookStore
from social_arb.studio.base import GeneratorProtocol, Studio
from social_arb.studio.mindmap import MindMapGenerator
from social_arb.studio.overview import OverviewGenerator, parse_sections


def default_studio(store: NotebookStore) -> Studio:
    """Wire up the v0 generator set against a given notebook store."""
    return Studio(
        store,
        generators={
            ArtifactKind.OVERVIEW: OverviewGenerator(),
            ArtifactKind.MIND_MAP: MindMapGenerator(),
        },
    )


__all__ = [
    "GeneratorProtocol",
    "MindMapGenerator",
    "OverviewGenerator",
    "Studio",
    "default_studio",
    "parse_sections",
]
