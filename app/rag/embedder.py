"""
embedder.py — local sentence embeddings via sentence-transformers.

Why local instead of an API: no cost, no rate limit, and embeddings run
fine on CPU for a project this size. all-MiniLM-L6-v2 is a small (~90MB),
well-regarded general-purpose embedding model — a standard default choice
for exactly this kind of retrieval task.

The model is loaded once and cached at module level (`_model`) because
loading it is the expensive part (~1-2s); embedding calls after that are
fast. First run downloads the model weights from Hugging Face — that
requires internet access once, then it's cached locally.
"""
from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

_MODEL_NAME = "all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of strings, returning an (n, 384) float32 array."""
    if not texts:
        return np.empty((0, 384), dtype="float32")
    model = _get_model()
    return model.encode(texts, convert_to_numpy=True).astype("float32")