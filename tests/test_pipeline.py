from unittest.mock import patch

import numpy as np

from app.rag.pipeline import search_filing_content


@patch("app.rag.pipeline.embed_texts")
@patch("app.rag.pipeline.fetch_filing_text")
@patch("app.rag.pipeline.search_filings")
def test_search_filing_content_success(mock_search, mock_fetch, mock_embed):
    mock_search.return_value = [{"url": "https://sec.gov/fake-filing.htm", "form_type": "10-K"}]
    mock_fetch.return_value = "Risk factors include competition and supply chain disruption. " * 50
    mock_embed.side_effect = [
        np.random.rand(3, 384).astype("float32"),
        np.random.rand(1, 384).astype("float32"),
    ]

    result = search_filing_content("Tesla", "What are the main risks?")

    assert "source_url" in result
    assert len(result["excerpts"]) > 0


@patch("app.rag.pipeline.search_filings")
def test_search_filing_content_no_filing_found(mock_search):
    mock_search.return_value = [{"error": "no results"}]

    result = search_filing_content("Unknown Co", "What are the risks?")

    assert "error" in result


@patch("app.rag.pipeline.fetch_filing_text")
@patch("app.rag.pipeline.search_filings")
def test_search_filing_content_fetch_fails(mock_search, mock_fetch):
    mock_search.return_value = [{"url": "https://sec.gov/fake.htm"}]
    mock_fetch.return_value = "error: failed to fetch filing - timeout"

    result = search_filing_content("Tesla", "risks?")

    assert "error" in result