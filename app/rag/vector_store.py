"""
vector_store.py — thin FAISS wrapper for chunk retrieval.

Why FAISS: free, local, no server to run, and fast enough for the handful
of chunks a single filing produces. This builds a fresh in-memory index
per research query rather than persisting one — a filing's chunks are
only needed for the duration of one research question, so there's nothing
worth persisting yet. A production version would cache per-company
indexes so repeat questions about the same filing don't re-embed it every
time — worth naming as the obvious next optimization.
"""
from __future__ import annotations

import faiss
import numpy as np


class ChunkIndex:
    """An in-memory FAISS index over a list of text chunks."""

    def __init__(self, chunks: list[str], embeddings: np.ndarray):
        self.chunks = chunks
        dim = embeddings.shape[1] if embeddings.size else 384
        self.index = faiss.IndexFlatL2(dim)
        if embeddings.size:
            self.index.add(embeddings)

    def query(self, query_embedding: np.ndarray, k: int = 4) -> list[str]:
        """Return the top-k most similar chunks to `query_embedding`."""
        if not self.chunks:
            return []
        k = min(k, len(self.chunks))
        _, indices = self.index.search(query_embedding.reshape(1, -1), k)
        return [self.chunks[i] for i in indices[0] if i != -1]
