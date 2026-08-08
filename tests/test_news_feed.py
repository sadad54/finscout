from unittest.mock import MagicMock, patch

from app.tools.news_feed import get_recent_headlines


@patch("app.tools.news_feed.feedparser.parse")
def test_get_recent_headlines_from_yahoo(mock_parse):
    mock_feed = MagicMock()
    mock_feed.entries = [
        {"title": "Tesla beats delivery estimates", "link": "https://a.com", "published": "2026-08-01"},
        {"title": "Tesla unveils new model", "link": "https://b.com", "published": "2026-08-02"},
    ]
    mock_parse.return_value = mock_feed

    headlines = get_recent_headlines("tsla", limit=5)

    assert len(headlines) == 2
    assert headlines[0]["title"] == "Tesla beats delivery estimates"
    mock_parse.assert_called_once()  # confirms it did NOT fall back to Google News


@patch("app.tools.news_feed.feedparser.parse")
def test_get_recent_headlines_falls_back_to_google(mock_parse):
    empty_feed = MagicMock()
    empty_feed.entries = []
    fallback_feed = MagicMock()
    fallback_feed.entries = [{"title": "Fallback headline", "link": "https://c.com", "published": "2026-08-03"}]
    mock_parse.side_effect = [empty_feed, fallback_feed]

    headlines = get_recent_headlines("TSLA")

    assert mock_parse.call_count == 2  # Yahoo tried first, then Google fallback
    assert headlines[0]["title"] == "Fallback headline"