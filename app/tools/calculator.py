"""
calculator.py — Tool: deterministic financial ratio math.

Why this exists: LLMs are unreliable at arithmetic. Every number that
reaches the final report should come from here or straight from
market_data.py — never from the model doing mental math. Pure stdlib,
zero dependencies, on purpose.
"""
from __future__ import annotations


def price_to_earnings(price: float, eps: float) -> float | None:
    """P/E = price / earnings-per-share. Returns None if eps is zero/invalid."""
    if not eps:
        return None
    return round(price / eps, 2)


def market_cap_to_revenue(market_cap: float, revenue: float) -> float | None:
    """Price-to-sales style ratio: market cap / revenue."""
    if not revenue:
        return None
    return round(market_cap / revenue, 2)


def pct_change(old: float, new: float) -> float | None:
    """Percentage change from `old` to `new`, e.g. 52-week-low to current price."""
    if not old:
        return None
    return round((new - old) / old * 100, 2)