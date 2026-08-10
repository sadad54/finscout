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

def gather_evidence_and_report(ticker: str, company: str) -> tuple[dict, dict]:
    """Gather evidence and synthesize it into a report dict (not yet rendered).

    Split out from run_research so the eval harness (Module 5) can score
    the report against the evidence it came from, without re-parsing
    rendered markdown back into structured data.
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
    return evidence, report


def run_research_events(ticker: str, company: str):
    """Run the research pipeline, yielding an event per stage instead of
    returning only the final markdown. Powers the `/research/stream` SSE
    endpoint. Deliberately separate from `gather_evidence_and_report` (used
    by the eval harness) rather than a refactor of it, so this addition
    carries zero risk to eval scoring.

    Events:
        {"type": "stage", "stage": str, "status": "start"}
        {"type": "stage", "stage": str, "status": "done", "result": Any}
        {"type": "final", "markdown": str}
    """
    yield {"type": "stage", "stage": "market_data", "status": "start"}
    market_data = get_market_snapshot(ticker)
    yield {"type": "stage", "stage": "market_data", "status": "done", "result": market_data}

    yield {"type": "stage", "stage": "news", "status": "start"}
    recent_news = get_recent_headlines(ticker)
    yield {"type": "stage", "stage": "news", "status": "done", "result": recent_news}

    yield {"type": "stage", "stage": "risk_factors", "status": "start"}
    risk_excerpts = search_filing_content(company, "main risk factors", top_k=3)
    yield {"type": "stage", "stage": "risk_factors", "status": "done", "result": risk_excerpts}

    yield {"type": "stage", "stage": "business_overview", "status": "start"}
    overview_excerpts = search_filing_content(
        company, "business overview and main products or services", top_k=3
    )
    yield {"type": "stage", "stage": "business_overview", "status": "done", "result": overview_excerpts}

    evidence = {
        "market_data": market_data,
        "recent_news": recent_news,
        "risk_factors_excerpts": risk_excerpts,
        "business_overview_excerpts": overview_excerpts,
    }
    report = generate_report(ticker, company, evidence)
    markdown = render_markdown(ticker, report)
    yield {"type": "final", "markdown": markdown}


def run_research(ticker: str, company: str) -> str:
    """Gather evidence on `company`/`ticker` and return a markdown research brief."""
    evidence, report = gather_evidence_and_report(ticker, company)
    return render_markdown(ticker, report)