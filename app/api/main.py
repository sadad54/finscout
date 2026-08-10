"""
main.py — FastAPI layer exposing FinScout as an HTTP service.

Why this module exists: the JD explicitly calls out "concept to
production" — a Python function nobody can call over the network isn't a
product. This wraps the two existing entry points (the open-ended agent
loop from Module 2, and the fixed research-brief pipeline from Module 4)
behind two REST endpoints, plus a health check.

This is intentionally a thin layer: FastAPI's job here is request
validation and routing, not business logic. All the actual work still
lives in app/agent and app/synthesis — the API layer should be swappable
(e.g. for a CLI, a Slack bot, or a different framework) without touching
those modules.
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agent.orchestrator import run_agent
from app.agent.research_flow import run_research

app = FastAPI(
    title="FinScout API",
    description="Public markets research agent - tool use, RAG, and agentic Q&A over free financial data sources.",
    version="0.1.0",
)

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="An open-ended research question")


class AskResponse(BaseModel):
    answer: str


class ResearchRequest(BaseModel):
    ticker: str = Field(..., min_length=1, description="Stock ticker, e.g. AAPL")
    company: str = Field(..., min_length=1, description="Company name, e.g. 'Apple Inc.'")


class ResearchResponse(BaseModel):
    ticker: str
    report_markdown: str


@app.get("/health")
def health() -> dict:
    """Basic liveness check - confirms the service is up, not that Groq is reachable."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Open-ended Q&A: the agent decides which tools to call (Module 2)."""
    try:
        answer = run_agent(request.question)
    except Exception as exc:
        # A tool-calling loop can fail in ways specific to the LLM provider
        # (rate limits, auth errors) that aren't the caller's fault to debug -
        # surface them as a 502, not a raw 500 stack trace.
        raise HTTPException(status_code=502, detail=f"agent failed: {exc}") from exc
    return AskResponse(answer=answer)


@app.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest) -> ResearchResponse:
    """Fixed research brief pipeline: gather evidence -> synthesize -> cite (Module 4)."""
    try:
        markdown = run_research(request.ticker, request.company)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"research pipeline failed: {exc}") from exc
    return ResearchResponse(ticker=request.ticker.upper(), report_markdown=markdown)