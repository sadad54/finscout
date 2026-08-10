from unittest.mock import MagicMock, patch

from app.tools.filings_search import fetch_filing_text, search_filings


@patch("app.tools.filings_search.requests.get")
def test_search_filings_parses_hits(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "0000320193-24-000123:aapl-ex211.htm",
                    "_source": {
                        "ciks": ["0000320193"],
                        "display_names": ["Apple Inc."],
                        "form": "10-K",
                        "file_type": "EX-21.1",
                        "file_date": "2024-11-01",
                    },
                },
                {
                    "_id": "0000320193-24-000123:aapl-10k.htm",
                    "_source": {
                        "ciks": ["0000320193"],
                        "display_names": ["Apple Inc."],
                        "form": "10-K",
                        "file_type": "10-K",
                        "file_date": "2024-11-01",
                    },
                }
            ]
        }
    }
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    results = search_filings("Apple", form_type="10-K")

    assert len(results) == 1
    assert results[0]["company"] == "Apple Inc."
    assert results[0]["form_type"] == "10-K"
    assert results[0]["accession_no"] == "000032019324000123"
    assert "aapl-10k.htm" in results[0]["url"]
    assert "aapl-ex211.htm" not in results[0]["url"]
    assert "/data/320193/" in results[0]["url"]


@patch("app.tools.filings_search.requests.get")
def test_search_filings_handles_failure(mock_get):
    mock_get.side_effect = ConnectionError("timeout")

    results = search_filings("Apple")

    assert len(results) == 1
    assert "error" in results[0]


@patch("app.tools.filings_search.requests.get")
def test_fetch_filing_text_truncates(mock_get):
    mock_resp = MagicMock()
    mock_resp.text = "x" * 100_000
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    text = fetch_filing_text("https://example.com/filing.htm", max_chars=10)

    assert text == "x" * 10


@patch("app.tools.filings_search.requests.get")
def test_fetch_filing_text_strips_markup_and_hidden_xbrl(mock_get):
    mock_resp = MagicMock()
    mock_resp.text = (
        "<html><ix:header><ix:nonNumeric>hidden xbrl fact</ix:nonNumeric></ix:header>"
        "<body><script>var x = 1;</script>"
        "<p>Item 1A. Risk Factors: we face intense competition.</p></body></html>"
    )
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    text = fetch_filing_text("https://example.com/filing.htm")

    assert "Item 1A. Risk Factors: we face intense competition." in text
    assert "hidden xbrl fact" not in text
    assert "var x = 1" not in text