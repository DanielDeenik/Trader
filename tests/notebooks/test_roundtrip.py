"""End-to-end: parse → chunk → embed → store → search returns the chunk.

Uses the deterministic embedder + sqlite store so it runs without any
optional deps, model downloads, or live databases.
"""
from social_arb.notebooks.chunker import Chunker, ChunkerConfig
from social_arb.notebooks.embedder import DeterministicEmbedder
from social_arb.notebooks.parsers import ContentHint, parse_blob
from social_arb.sources import ChunkWithVector, SqliteStore


def test_parse_chunk_embed_store_search_roundtrip():
    text = (
        "AMD reported strong Q1 earnings. Divergence score 70.4. "
        "Coherence 100. Lifecycle Validating. The thesis recommends "
        "a build_thesis with Kelly 0.25 sizing."
    ) * 5  # ensure multiple chunks

    # Parse
    parsed = parse_blob(text, ContentHint(filename="amd-thesis.txt", title_hint="AMD Q1 thesis"))
    assert parsed.title == "AMD Q1 thesis"

    # Chunk
    chunker = Chunker(ChunkerConfig(chunk_size_tokens=20, chunk_overlap_tokens=4, min_chunk_tokens=1))
    source, chunks = chunker.chunk(parsed)
    assert len(chunks) >= 2

    # Embed
    embedder = DeterministicEmbedder(dim=32)
    vectors = embedder.embed_batch([c.text for c in chunks])
    chunks_with_vec = [
        ChunkWithVector(chunk=c, vector=v) for c, v in zip(chunks, vectors)
    ]

    # Store
    store = SqliteStore()
    store.save(source, chunks_with_vec)

    # Search using the embedding of the first chunk's text — it should
    # be the top hit because it's the same text, same embedding.
    query_vector = embedder.embed(chunks[0].text)
    hits = store.search_similar(query_vector, k=3)
    assert len(hits) >= 1
    assert hits[0].chunk.id == chunks[0].id
    assert hits[0].score > 0.99


def test_search_filter_by_source_id():
    store = SqliteStore()
    embedder = DeterministicEmbedder(dim=16)
    chunker = Chunker(ChunkerConfig(chunk_size_tokens=20, chunk_overlap_tokens=4, min_chunk_tokens=1))

    for label in ["alpha-text-content", "beta-text-content"]:
        parsed = parse_blob(label * 10, ContentHint(filename=f"{label}.txt"))
        src, chunks = chunker.chunk(parsed)
        vecs = embedder.embed_batch([c.text for c in chunks])
        store.save(src, [ChunkWithVector(chunk=c, vector=v) for c, v in zip(chunks, vecs)])

    sources = store.list_sources()
    assert len(sources) == 2
    only_alpha = [s for s in sources if "alpha" in s.title][0]

    # Search restricted to alpha.
    q = embedder.embed("alpha-text-content")
    hits = store.search_similar(q, k=10, filter_source_ids=[only_alpha.id])
    assert all(h.chunk.source_id == only_alpha.id for h in hits)
