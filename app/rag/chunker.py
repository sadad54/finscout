"""
chunker.py — split raw filing text into overlapping chunks for embedding.

Why this exists: embedding models work best on short-ish inputs, and
retrieval quality depends heavily on chunk size. Overlap prevents losing
meaning at chunk boundaries — a fact split exactly at a cut point would
otherwise get sliced across two disconnected chunks.

This is a simple word-count sliding window, not sentence-aware chunking.
That's a deliberate simplification for a capstone project — sentence-aware
or semantic chunking is the natural upgrade path in production, and is
worth naming if asked "how would you improve this."
"""
from __future__ import annotations


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 40) -> list[str]:
    """Split `text` into overlapping chunks of ~`chunk_size` words.

    `overlap` words repeat between consecutive chunks so a fact sitting at
    a chunk boundary isn't split across two disconnected chunks.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    step = chunk_size - overlap
    for start in range(0, len(words), step):
        chunk = " ".join(words[start:start + chunk_size])
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break
    return chunks