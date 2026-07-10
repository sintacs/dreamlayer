"""Retrieval quality regression: a fixed benchmark of memories + queries with a
precision@3 floor, so a change that quietly degrades recall fails loudly. Uses
the deterministic mock embedder (always available); auto-upgrades the floor when
a real local embedder is installed."""
from dreamlayer.memory.db import MemoryDB
from dreamlayer.memory.embeddings import MockEmbeddingProvider
from dreamlayer.memory.embedder_local import LocalEmbeddingProvider
from dreamlayer.memory.retrieval import Retriever

# (summary, the query that should retrieve it in its top-3)
BENCH = [
    ("snake plant on the windowsill, water every two weeks", "how often water the plant"),
    ("left the bike locked at the north rack on 4th and Alder", "where is my bike"),
    ("Marcus is owed the signed lease by Friday", "what do I owe Marcus"),
    ("Priya teaches ceramics, met at the Overpass show", "who is Priya"),
    ("the cafe on Pine street is cash only", "cafe that takes cash"),
    ("dentist appointment on Tuesday at 3pm", "when is the dentist"),
    ("passport is in the top drawer of the desk", "where is my passport"),
    ("wifi password for the studio is bluewren", "studio wifi password"),
    ("Mom's birthday is March 14th", "when is mom's birthday"),
    ("parked the car on level 3 of the garage", "which level did I park"),
    ("the red wine from Rioja was 18 dollars last time", "price of the rioja wine"),
    ("gym membership renews on the first of the month", "when does the gym renew"),
]

QUERIES = [
    ("how often water the plant", "snake plant"),
    ("where is my bike", "bike"),
    ("what do I owe Marcus", "Marcus"),
    ("who is Priya", "Priya"),
    ("cafe that takes cash", "cash only"),
    ("when is the dentist", "dentist"),
    ("where is my passport", "passport"),
    ("studio wifi password", "wifi"),
    ("when is mom's birthday", "birthday"),
    ("which level did I park", "level 3"),
    ("price of the rioja wine", "Rioja"),
    ("when does the gym renew", "gym"),
]


def _seed(embedder):
    db = MemoryDB()
    r = Retriever(db, embedder)
    for summary, _q in BENCH:
        mid = db.add_memory("note", summary, embedding=embedder.embed(summary))
        r.index_memory(mid, embedder.embed(summary))
    return db, r


def _precision_at_3(embedder) -> float:
    _db, r = _seed(embedder)
    hits = 0
    for query, needle in QUERIES:
        top3 = r.search(query, top_k=3)
        if any(needle.lower() in m["summary"].lower() for _s, m in top3):
            hits += 1
    return hits / len(QUERIES)


class TestRetrievalQuality:
    def test_mock_embedder_precision_floor(self):
        # the 32-d hash embedder is weak by design; the floor guards against a
        # regression making it *worse*, not against it being great.
        p = _precision_at_3(MockEmbeddingProvider())
        assert p >= 0.5, f"mock precision@3 regressed to {p:.2f}"

    def test_local_embedder_beats_mock_when_available(self):
        if not LocalEmbeddingProvider.available:
            import pytest
            pytest.skip("sentence-transformers not installed")
        local = _precision_at_3(LocalEmbeddingProvider())
        assert local >= 0.85, f"local precision@3 regressed to {local:.2f}"
