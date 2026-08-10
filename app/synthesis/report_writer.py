"""
report_writer.py — turn raw tool/RAG outputs into a structured, cited
research brief.

Why this is a separate step from the raw agent loop (Module 2): letting the
model free-associate a final answer from tool results works fine for a
single question, but a "research brief" needs a consistent shape (same
sections, every time) and an explicit citation trail — the "responsible AI"
bullet in the JD. This module forces that structure with a JSON-mode prompt
instead of hoping the model formats things consistently on its own.
"""
from __future__ import annotations

import json
import os

from groq import Groq

MODEL = "llama-3.3-70b-versatile"

REPORT_SCHEMA_PROMPT = """You are a financial research analyst. You will be
given raw evidence about a company (price/fundamentals data, recent news
headlines, and excerpts from their SEC filing). Write a structured research
brief using ONLY the evidence provided — never invent numbers, events, or
facts that aren't in the evidence. If a piece of evidence is missing or
contains an error, say so honestly in the relevant section instead of
making something up.

Respond with ONLY a JSON object (no markdown, no preamble) with this exact
shape:
{
  "overview": "2-3 sentence summary of what the company does, grounded in the filing excerpts",
  "financial_snapshot": "1-2 sentences on price, market cap, P/E — grounded in the market data",
  "recent_news_summary": "1-2 sentences summarizing the recent headlines, or noting none were found",
  "risk_factors": ["risk 1 from the filing", "risk 2 from the filing", "..."],
  "sources": ["yfinance (live market data)", "SEC EDGAR filing: <url if available>", "Yahoo/Google News RSS"]
}"""


def generate_report(ticker: str, company: str, evidence: dict) -> dict:
    """Call Groq to synthesize `evidence` into a structured report dict.

    Returns the parsed JSON report on success, or {"error": ...} if the
    model's response wasn't valid JSON (rare with response_format enforced,
    but a call to an LLM should never assume the response is well-formed).
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    user_content = (
        f"Ticker: {ticker}\nCompany: {company}\n\n"
        f"Evidence (JSON):\n{json.dumps(evidence, indent=2)}"
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": REPORT_SCHEMA_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"error": f"model returned invalid JSON: {exc}", "raw": raw}


def render_markdown(ticker: str, report: dict) -> str:
    """Render a report dict (from generate_report) into a readable markdown brief."""
    if "error" in report:
        return f"# {ticker} — Research Brief\n\n_Report generation failed: {report['error']}_"

    risks = "\n".join(f"- {r}" for r in report.get("risk_factors", []))
    sources = "\n".join(f"- {s}" for s in report.get("sources", []))

    return f"""# {ticker} — Research Brief

## Overview
{report.get('overview', 'Not available.')}

## Financial Snapshot
{report.get('financial_snapshot', 'Not available.')}

## Recent News
{report.get('recent_news_summary', 'Not available.')}

## Risk Factors
{risks or '- Not available.'}

## Sources
{sources or '- Not available.'}
"""