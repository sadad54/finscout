"""tool: fetches live price and fundamental data for a ticker. 

why this exists: the agent needs numeric grounding (price, market cap, P/E) that an LLM must never be left to hallucinate. this wraps yfinance and returns a plain dict so it can be dropped striaght into Groq tool-call result.

"""

from __future__ import annotations

import yfinance as yf

def get_market_snapshot(ticker: str)-> dict:
    """returns a snapshot of current price and key fundamentals for 'ticker'"""
    ticker = ticker.strip().upper()
    try:
        info = yf.Ticker(ticker).info
    except Exception as exc: #yfinance can throw a variety of exceptions, including network errors and invalid tickers
        return {"ticker": ticker, "error":f"failed to fetch market data:{exc}"}

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    if not info or price is None:
        return {"ticker": ticker, "error": "no data returned -- check the ticker symbol"}

    return{
        "ticker": ticker,
        "price": price,
        "currency": info.get("currency"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "sector": info.get("sector"),
    }