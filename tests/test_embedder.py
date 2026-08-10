from unittest.mock import MagicMock, patch

import numpy as np

from app.rag import embedder


@patch("app.rag.embedder.SentenceTransformer")
def test_embed_texts_calls_model(mock_st_cls):
    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros((2, 384), dtype="float32")
    mock_st_cls.return_value = mock_model
    embedder._model = None  # reset the module-level cache between tests

    result = embedder.embed_texts(["hello", "world"])

    assert result.shape == (2, 384)
    mock_model.encode.assert_called_once()


def test_embed_texts_empty_list():
    embedder._model = None
    result = embedder.embed_texts([])
    assert result.shape == (0, 384)