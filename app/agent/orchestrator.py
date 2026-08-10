"""
orchestrator.py — the agent loop: plan -> call tools -> observe -> repeat.

This is the core "agentic workflow" piece of FinScout. It's a hand-rolled
loop, not a framework (LangGraph, CrewAI, etc.) - on purpose, so every step
of how tool-calling actually works is something you built and can explain,
not library internals you're pointing at.

How it works, in one paragraph: we send Groq a system prompt + the user's
question + a JSON schema describing which tools exist. The model can either
answer directly or ask to call one or more tools. If it asks for tools, we
run the real Python functions, append their results as "tool" messages, and
send the whole conversation back to the model. This repeats until the model
stops asking for tools and gives a final answer, or we hit a safety cap on
iterations.
"""
from __future__ import annotations

import json
import os
from typing import Any, cast

from groq import Groq
from groq.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from app.tools.calculator import price_to_earnings
from app.tools.filings_search import search_filings
from app.tools.market_data import get_market_snapshot
from app.tools.news_feed import get_recent_headlines

MODEL = "llama-3.3-70b-versatile"
MAX_ITERATIONS = 6  # safety cap so a confused model can't loop forever and burn quota

SYSTEM_PROMPT = (
    "You are FinScout, a research assistant for public company analysis. "
    "You have tools to fetch live market data, search SEC filings, fetch "
    "recent news, and compute financial ratios. Always use tools to get "
    "real numbers instead of guessing. Cite where each fact came from "
    "(e.g. 'per yfinance', 'per the 2024 10-K'). If a tool returns an "
    "error, say so honestly instead of making up a number."
)

# Tool schemas in Groq/OpenAI function-calling format. This is the contract
# the model sees; the actual Python callables live in TOOL_REGISTRY below.
# Keeping schema and implementation separate is deliberate: the model only
# ever sees names, descriptions, and typed parameters - never your code.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_market_snapshot",
            "description": "Get current price and key fundamentals (P/E, market cap, 52-week range, sector) for a stock ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol, e.g. AAPL"},
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_filings",
            "description": "Search SEC EDGAR for a company's recent filings (e.g. 10-K annual reports, 10-Q quarterly reports).",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Company name, e.g. 'Apple Inc'"},
                    "form_type": {"type": "string", "description": "Filing type, e.g. '10-K' or '10-Q'"},
                },
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_headlines",
            "description": "Get recent news headlines for a stock ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol, e.g. TSLA"},
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "price_to_earnings",
            "description": "Compute the P/E ratio given a price and earnings-per-share.",
            "parameters": {
                "type": "object",
                "properties": {
                    "price": {"type": "number"},
                    "eps": {"type": "number"},
                },
                "required": ["price", "eps"],
            },
        },
    },
]

# Maps tool name -> the actual Python function that does the work.
TOOL_REGISTRY = {
    "get_market_snapshot": lambda ticker: get_market_snapshot(ticker),
    "search_filings": lambda company, form_type="10-K": search_filings(company, form_type),
    "get_recent_headlines": lambda ticker: get_recent_headlines(ticker),
    "price_to_earnings": lambda price, eps: {"pe_ratio": price_to_earnings(price, eps)},
}


def _run_tool(name: str, arguments: dict) -> dict:
    """Execute a registered tool and always return a JSON-serializable dict.

    An unknown tool name or bad arguments becomes an {"error": ...} payload
    instead of raising - a malformed tool call from the model should not
    crash the whole research run, it should be something the model can see
    and recover from on the next turn.
    """
    if name not in TOOL_REGISTRY:
        return {"error": f"unknown tool: {name}"}
    try:
        return TOOL_REGISTRY[name](**arguments)
    except Exception as exc:
        return {"error": f"tool '{name}' failed: {exc}"}


def run_agent(question: str, verbose: bool = False) -> str:
    """Run the agent loop for a single research question, return the final answer.

    `verbose=True` prints each tool call as it happens - useful while
    developing, and useful in an interview demo to show the reasoning
    trace instead of just the final text.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=cast(list[ChatCompletionToolParam], TOOL_SCHEMAS),
            tool_choice="auto",
        )
        choice = response.choices[0].message

        if not choice.tool_calls:
            return choice.content or ""  # model is done - no more tools requested

        # The model asked for one or more tool calls. Append its request to
        # history first (the API requires the assistant's tool_calls message
        # to precede the tool result messages), then run each tool.
        messages.append(cast(ChatCompletionMessageParam, choice.model_dump()))

        for call in choice.tool_calls:
            args = json.loads(call.function.arguments)
            if verbose:
                print(f"[tool call] {call.function.name}({args})")
            result = _run_tool(call.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

    return "I hit the maximum number of research steps without reaching a final answer - try narrowing the question."