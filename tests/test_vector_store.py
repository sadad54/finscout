import numpy as np

from app.rag.vector_store import ChunkIndex


def test_chunk_index_returns_closest_chunk():
    chunks = ["chunk about apples", "chunk about cars", "chunk about oranges"]
    embeddings = np.array([
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.9, 0.1, 0.0],
    ], dtype="float32")

    index = ChunkIndex(chunks, embeddings)
    query = np.array([1.0, 0.0, 0.0], dtype="float32")

    results = index.query(query, k=2)

    assert results[0] == "chunk about apples"
    assert "chunk about oranges" in results
    assert "chunk about cars" not in results


def test_chunk_index_empty():
    index = ChunkIndex([], np.empty((0, 3), dtype="float32"))
    assert index.query(np.zeros(3, dtype="float32")) == []