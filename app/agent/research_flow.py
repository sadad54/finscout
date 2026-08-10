"""
research_flow.py — the "full report" pipeline: gather evidence from every
tool, then hand it to report_writer for structured synthesis.

This is deliberately NOT the same code path as orchestrator.py's run_agent.
run_agent is for open-ended single questions where the model decides which
tools to call. This flow is for the specific, repeatable "give me a full
research brief on X" request, where we always want the same evidence
gathered in the same order — a fixed pipeline is more reliable and cheaper
(fewer Groq calls) than asking the model to plan out four or five tool
calls itself every time.

Interview note: this is a good example of "not every problem needs an
agent" — a deterministic pipeline is the better tool when the steps don't
actually vary by question. The agent loop (Module 2) is for open-ended
Q&A; this fixed flow is for a known, repeatable report shape.
"""
from __future__ import annotations

from app.rag.pipeline import search_filing_content
from app.synthesis.report_writer import generate_report, render_markdown
from app.tools.market_data import get_market_snapshot
from app.tools.news_feed import get_recent_headlines


def run_research(ticker: str, company: str) -> str:
    """Gather evidence on `company`/`ticker` and return a markdown research brief.

    Note: this takes both a ticker (for market_data/news_feed, which are
    ticker-keyed) and a company name (for EDGAR search, which is name-keyed).
    Resolving one from the other automatically is a reasonable next feature
    — SEC publishes a free ticker-to-company lookup at
    https://www.sec.gov/files/company_tickers.json — but is out of scope
    for this module.
    """
    evidence = {
        "market_data": get_market_snapshot(ticker),
        "recent_news": get_recent_headlines(ticker),
        "risk_factors_excerpts": search_filing_content(company, "main risk factors", top_k=3),
        "business_overview_excerpts": search_filing_content(
            company, "business overview and main products or services", top_k=3
        ),
    }

    report = generate_report(ticker, company, evidence)
    return render_markdown(ticker, report)