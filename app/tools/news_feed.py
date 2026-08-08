"""
news_feed.py — Tool: fetch recent headlines for a company from free RSS feeds.

Why this exists: gives the agent a lightweight, no-API-key read on recent
sentiment/events, separate from the deep filings text pulled by
filings_search.py.

Uses Yahoo Finance's per-ticker RSS feed (free, no key). Falls back to
Google News RSS if Yahoo's feed comes back empty (Yahoo has been known to
retire feeds without notice — the fallback keeps this tool useful either way).
"""
from __future__ import annotations

import feedparser

YAHOO_RSS = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}"


def get_recent_headlines(ticker: str, limit: int = 8) -> list[dict]:
    """Return up to `limit` recent headlines for `ticker`.

    Each item: {title, link, published}. Falls back to Google News RSS
    (searching "<ticker> stock") if the Yahoo feed returns nothing.
    """
    ticker = ticker.strip().upper()
    feed = feedparser.parse(YAHOO_RSS.format(ticker=ticker))
    entries = feed.entries

    if not entries:
        feed = feedparser.parse(GOOGLE_NEWS_RSS.format(query=f"{ticker}+stock"))
        entries = feed.entries

    return [
        {"title": e.get("title"), "link": e.get("link"), "published": e.get("published")}
        for e in entries[:limit]
    ]