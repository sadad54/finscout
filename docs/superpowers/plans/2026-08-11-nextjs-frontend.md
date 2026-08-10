# FinScout Next.js Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SSE streaming to the FastAPI backend's agent/research pipelines and build a Next.js frontend with two first-class pages (Ask chat, Research Brief) in a dark terminal-grade fintech style, per `docs/superpowers/specs/2026-08-11-nextjs-frontend-design.md`.

**Architecture:** Backend tasks add non-breaking generator variants (`run_agent_events`, `run_research_events`) alongside the existing `run_agent`/`run_research` functions, exposed via two new `/ask/stream` and `/research/stream` SSE endpoints. Frontend is a new `frontend/` Next.js App Router app that consumes those SSE endpoints via `fetch` + manual stream parsing (not `EventSource`, since both endpoints need POST bodies).

**Tech Stack:** FastAPI (existing), Next.js 14 App Router, TypeScript, Tailwind CSS, hand-authored shadcn-style primitives (Radix conventions without the interactive CLI), Framer Motion, react-markdown.

## Global Constraints

- `run_agent(question, verbose=False) -> str` and `run_research(ticker, company) -> str` keep their exact current signatures and behavior — `scripts/ask.py`, `app/eval/run_eval.py` (via `gather_evidence_and_report`), and existing tests must keep working with zero changes.
- `gather_evidence_and_report` in `app/agent/research_flow.py` is not modified.
- CORS default allowed origin is `http://localhost:3000`, overridable via the `FRONTEND_ORIGIN` env var.
- No automated frontend test suite (per spec non-goals) — frontend tasks verify via `npm run build` (typecheck + build), final task is manual in-browser verification against the real backend.
- Dark theme only, no light-mode toggle — background `hsl(240 6% 4%)`, single accent green for interactive/positive, red reserved only for negative deltas, Geist Sans for UI text, Geist Mono for all numeric/ticker data.

---

## Backend Tasks

### Task 1: CORS middleware on the FastAPI app

**Files:**
- Modify: `app/api/main.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Produces: no new functions; `app` now accepts cross-origin requests from `FRONTEND_ORIGIN` (default `http://localhost:3000`).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_api.py`:

```python
def test_cors_allows_frontend_origin():
    resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_api.py::test_cors_allows_frontend_origin -v`
Expected: FAIL (no `access-control-allow-origin` header yet)

- [ ] **Step 3: Add CORS middleware**

In `app/api/main.py`, add near the top (after the existing imports) and right after `app = FastAPI(...)`:

```python
import os

from fastapi.middleware.cors import CORSMiddleware
```

```python
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_api.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add app/api/main.py tests/test_api.py
git commit -m "feat: add CORS middleware to FastAPI app for frontend access"
```

---

### Task 2: Streaming events for the agent loop (`run_agent_events`)

**Files:**
- Modify: `app/agent/orchestrator.py`
- Modify: `tests/test_orchestrator.py`

**Interfaces:**
- Produces: `run_agent_events(question: str, verbose: bool = False)` — generator yielding one of:
  - `{"type": "tool_call", "tool": str, "args": dict}`
  - `{"type": "tool_result", "tool": str, "result": dict}`
  - `{"type": "final", "content": str}`
- `run_agent(question, verbose=False) -> str` keeps its exact current signature/behavior — becomes a thin wrapper draining `run_agent_events`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_orchestrator.py` (add `run_agent_events` to the existing import line):

```python
from app.agent.orchestrator import _run_tool, run_agent, run_agent_events
```

```python
@patch("app.agent.orchestrator.Groq")
def test_run_agent_events_yields_tool_call_then_final(mock_groq_cls, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_groq_cls.return_value = mock_client

    tool_call = _make_tool_call("call_1", "get_market_snapshot", {"ticker": "NVDA"})
    first_message = MagicMock()
    first_message.tool_calls = [tool_call]
    first_message.model_dump.return_value = {"role": "assistant", "tool_calls": [tool_call]}
    first_response = MagicMock(choices=[MagicMock(message=first_message)])

    second_message = MagicMock()
    second_message.tool_calls = None
    second_message.content = "NVDA is trading at $120, per yfinance."
    second_response = MagicMock(choices=[MagicMock(message=second_message)])

    mock_client.chat.completions.create.side_effect = [first_response, second_response]

    with patch(
        "app.agent.orchestrator.get_market_snapshot",
        return_value={"ticker": "NVDA", "price": 120},
    ):
        events = list(run_agent_events("What is NVDA trading at?"))

    assert events[0] == {"type": "tool_call", "tool": "get_market_snapshot", "args": {"ticker": "NVDA"}}
    assert events[1] == {
        "type": "tool_result",
        "tool": "get_market_snapshot",
        "result": {"ticker": "NVDA", "price": 120},
    }
    assert events[2] == {"type": "final", "content": "NVDA is trading at $120, per yfinance."}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_orchestrator.py::test_run_agent_events_yields_tool_call_then_final -v`
Expected: FAIL with `ImportError: cannot import name 'run_agent_events'`

- [ ] **Step 3: Refactor orchestrator.py**

In `app/agent/orchestrator.py`, replace the entire `run_agent` function (from `def run_agent(question: str, verbose: bool = False) -> str:` to the end of the file) with:

```python
def run_agent_events(question: str, verbose: bool = False):
    """Run the agent loop, yielding an event per step instead of returning
    only the final answer. Powers both `run_agent` below and the
    `/ask/stream` SSE endpoint - one implementation, two consumers.

    Events:
        {"type": "tool_call", "tool": str, "args": dict}
        {"type": "tool_result", "tool": str, "result": dict}
        {"type": "final", "content": str}
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for _ in range(MAX_ITERATIONS):
        for attempt in range(TOOL_CALL_RETRIES + 1):
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=cast(list[ChatCompletionToolParam], TOOL_SCHEMAS),
                    tool_choice="auto",
                )
                break
            except BadRequestError as exc:
                is_malformed_tool_call = (
                    isinstance(exc.body, dict)
                    and exc.body.get("error", {}).get("code") == "tool_use_failed"
                )
                if not is_malformed_tool_call or attempt == TOOL_CALL_RETRIES:
                    raise
                if verbose:
                    print(f"[retry] malformed tool call from model, retrying ({attempt + 1}/{TOOL_CALL_RETRIES})")
        choice = response.choices[0].message

        if not choice.tool_calls:
            yield {"type": "final", "content": choice.content or ""}
            return

        # The model asked for one or more tool calls. Append its request to
        # history first (the API requires the assistant's tool_calls message
        # to precede the tool result messages), then run each tool.
        messages.append(cast(ChatCompletionMessageParam, {
            "role": "assistant",
            "content": choice.content,
            "tool_calls": [tc.model_dump() for tc in choice.tool_calls],
        }))

        for call in choice.tool_calls:
            args = json.loads(call.function.arguments)
            if verbose:
                print(f"[tool call] {call.function.name}({args})")
            yield {"type": "tool_call", "tool": call.function.name, "args": args}
            result = _run_tool(call.function.name, args)
            yield {"type": "tool_result", "tool": call.function.name, "result": result}
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

    yield {
        "type": "final",
        "content": "I hit the maximum number of research steps without reaching a final answer - try narrowing the question.",
    }


def run_agent(question: str, verbose: bool = False) -> str:
    """Run the agent loop for a single research question, return the final answer.

    Thin wrapper over `run_agent_events` - drains the generator and returns
    just the final answer, for callers that only need the end result (CLI,
    eval harness).
    """
    final = ""
    for event in run_agent_events(question, verbose=verbose):
        if event["type"] == "final":
            final = event["content"]
    return final
```

- [ ] **Step 4: Run tests to verify everything passes**

Run: `python -m pytest tests/test_orchestrator.py -v`
Expected: all PASS, including the pre-existing `test_run_agent_calls_tool_then_answers` and `test_run_agent_stops_at_max_iterations` (behavior is unchanged, only refactored into a generator).

- [ ] **Step 5: Commit**

```bash
git add app/agent/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: extract run_agent_events generator for streaming tool-call events"
```

---

### Task 3: Streaming events for the research pipeline (`run_research_events`)

**Files:**
- Modify: `app/agent/research_flow.py`
- Modify: `tests/test_research_flow.py`

**Interfaces:**
- Produces: `run_research_events(ticker: str, company: str)` — generator yielding one of:
  - `{"type": "stage", "stage": str, "status": "start"}`
  - `{"type": "stage", "stage": str, "status": "done", "result": Any}`
  - `{"type": "final", "markdown": str}`
  - `stage` is one of `"market_data"`, `"news"`, `"risk_factors"`, `"business_overview"`.
- `run_research` and `gather_evidence_and_report` are **not modified** — `run_research_events` is additive, duplicating the evidence-gathering calls with per-stage events, so the eval harness's dependency on `gather_evidence_and_report` carries zero risk from this change.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_research_flow.py` (add `run_research_events` to the existing import line):

```python
from app.agent.research_flow import run_research, run_research_events
```

```python
@patch("app.agent.research_flow.render_markdown")
@patch("app.agent.research_flow.generate_report")
@patch("app.agent.research_flow.search_filing_content")
@patch("app.agent.research_flow.get_recent_headlines")
@patch("app.agent.research_flow.get_market_snapshot")
def test_run_research_events_yields_stage_then_final(
    mock_market, mock_news, mock_filing, mock_generate, mock_render
):
    mock_market.return_value = {"ticker": "TSLA", "price": 250}
    mock_news.return_value = [{"title": "Tesla news"}]
    mock_filing.side_effect = [
        {"source_url": "url1", "excerpts": ["risk excerpt"]},
        {"source_url": "url1", "excerpts": ["overview excerpt"]},
    ]
    mock_generate.return_value = {"overview": "..."}
    mock_render.return_value = "# TSLA — Research Brief\n..."

    events = list(run_research_events("TSLA", "Tesla, Inc."))

    stage_names = [e["stage"] for e in events if e["type"] == "stage"]
    assert stage_names == [
        "market_data", "market_data",
        "news", "news",
        "risk_factors", "risk_factors",
        "business_overview", "business_overview",
    ]
    assert events[4] == {
        "type": "stage", "stage": "risk_factors", "status": "done",
        "result": {"source_url": "url1", "excerpts": ["risk excerpt"]},
    }
    assert events[-1] == {"type": "final", "markdown": "# TSLA — Research Brief\n..."}
    mock_market.assert_called_once_with("TSLA")
    assert mock_filing.call_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_research_flow.py::test_run_research_events_yields_stage_then_final -v`
Expected: FAIL with `ImportError: cannot import name 'run_research_events'`

- [ ] **Step 3: Add run_research_events**

In `app/agent/research_flow.py`, append after `gather_evidence_and_report` (before `run_research`):

```python
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
```

- [ ] **Step 4: Run tests to verify everything passes**

Run: `python -m pytest tests/test_research_flow.py -v`
Expected: all PASS, including the pre-existing `test_run_research_gathers_all_evidence_and_synthesizes`.

- [ ] **Step 5: Commit**

```bash
git add app/agent/research_flow.py tests/test_research_flow.py
git commit -m "feat: add run_research_events generator for streaming pipeline progress"
```

---

### Task 4: SSE streaming endpoints (`/ask/stream`, `/research/stream`)

**Files:**
- Modify: `app/api/main.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: `run_agent_events(question)` from Task 2, `run_research_events(ticker, company)` from Task 3.
- Produces: `POST /ask/stream` and `POST /research/stream`, each returning `text/event-stream` responses where each event is a `data: {json}\n\n` frame. A generator exception mid-stream is turned into a final `{"type": "error", "detail": str}` frame.

- [ ] **Step 1: Write the failing tests**

Add `import json` near the top of `tests/test_api.py`, and add a parsing helper + tests:

```python
def _parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.strip().split("\n\n"):
        if block.startswith("data: "):
            events.append(json.loads(block[len("data: "):]))
    return events


@patch("app.api.main.run_agent_events")
def test_ask_stream_emits_events(mock_run_agent_events):
    mock_run_agent_events.return_value = iter([
        {"type": "tool_call", "tool": "get_market_snapshot", "args": {"ticker": "NVDA"}},
        {"type": "tool_result", "tool": "get_market_snapshot", "result": {"price": 120}},
        {"type": "final", "content": "NVDA is trading at $120."},
    ])

    resp = client.post("/ask/stream", json={"question": "What's NVDA at?"})

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(resp.text)
    assert events[0]["type"] == "tool_call"
    assert events[-1] == {"type": "final", "content": "NVDA is trading at $120."}


@patch("app.api.main.run_agent_events")
def test_ask_stream_emits_error_event_on_failure(mock_run_agent_events):
    def _boom():
        raise RuntimeError("Groq API down")
        yield  # pragma: no cover - makes this a generator function

    mock_run_agent_events.return_value = _boom()

    resp = client.post("/ask/stream", json={"question": "anything"})

    events = _parse_sse(resp.text)
    assert events[-1]["type"] == "error"
    assert "Groq API down" in events[-1]["detail"]


@patch("app.api.main.run_research_events")
def test_research_stream_emits_stage_and_final_events(mock_run_research_events):
    mock_run_research_events.return_value = iter([
        {"type": "stage", "stage": "market_data", "status": "start"},
        {"type": "stage", "stage": "market_data", "status": "done", "result": {"price": 250}},
        {"type": "final", "markdown": "# TSLA — Research Brief\n..."},
    ])

    resp = client.post("/research/stream", json={"ticker": "TSLA", "company": "Tesla, Inc."})

    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    assert events[0] == {"type": "stage", "stage": "market_data", "status": "start"}
    assert events[-1]["type"] == "final"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api.py -v`
Expected: FAIL — `/ask/stream` and `/research/stream` return 404 (routes don't exist yet).

- [ ] **Step 3: Add streaming endpoints**

In `app/api/main.py`, update imports:

```python
from __future__ import annotations

import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.orchestrator import run_agent, run_agent_events
from app.agent.research_flow import run_research, run_research_events
```

Append at the end of the file:

```python
def _sse_event(payload: dict) -> str:
    """Format one event as a Server-Sent Events data frame."""
    return f"data: {json.dumps(payload)}\n\n"


def _sse_stream(events):
    """Wrap an event generator as SSE frames, turning a mid-stream exception
    into a final error event instead of a raw 500 - once streaming has
    started the HTTP status is already committed, so an exception can't be
    surfaced as a normal error response."""
    try:
        for event in events:
            yield _sse_event(event)
    except Exception as exc:
        yield _sse_event({"type": "error", "detail": str(exc)})


@app.post("/ask/stream")
def ask_stream(request: AskRequest) -> StreamingResponse:
    """Streaming variant of /ask - emits tool_call/tool_result/final events."""
    return StreamingResponse(
        _sse_stream(run_agent_events(request.question)),
        media_type="text/event-stream",
    )


@app.post("/research/stream")
def research_stream(request: ResearchRequest) -> StreamingResponse:
    """Streaming variant of /research - emits per-stage progress events."""
    return StreamingResponse(
        _sse_stream(run_research_events(request.ticker, request.company)),
        media_type="text/event-stream",
    )
```

- [ ] **Step 4: Run tests to verify everything passes**

Run: `python -m pytest tests/test_api.py -v`
Expected: all PASS

- [ ] **Step 5: Run the full backend test suite**

Run: `python -m pytest tests/ -v`
Expected: all PASS (confirms no regressions in Tasks 1-4 combined)

- [ ] **Step 6: Commit**

```bash
git add app/api/main.py tests/test_api.py
git commit -m "feat: add /ask/stream and /research/stream SSE endpoints"
```

---

## Frontend Tasks

### Task 5: Scaffold the Next.js app, design tokens, fonts

**Files:**
- Create: `frontend/` (via `create-next-app`)
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/globals.css`
- Modify: `frontend/tailwind.config.ts`
- Create: `frontend/.env.local`

**Interfaces:**
- Produces: Tailwind color tokens `background`, `foreground`, `card`, `border`, `muted-foreground`, `accent-green`, `accent-red`; font classes `font-sans` (Geist Sans), `font-mono` (Geist Mono); env var `NEXT_PUBLIC_API_URL`.

- [ ] **Step 1: Scaffold with create-next-app**

Run from the repo root (`d:/RAG/finscout`):

```bash
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias "@/*" --use-npm --yes
```

Expected: `frontend/` created with `package.json`, `app/`, `tailwind.config.ts`, etc.

- [ ] **Step 2: Install the Geist font package**

```bash
cd frontend && npm install geist
```

- [ ] **Step 3: Set design tokens in globals.css**

Replace the contents of `frontend/app/globals.css` with:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --background: 240 6% 4%;
  --foreground: 0 0% 95%;
  --card: 240 5% 7%;
  --border: 240 4% 16%;
  --muted-foreground: 240 4% 60%;
  --accent-green: 152 69% 45%;
  --accent-red: 0 72% 55%;
}

body {
  background-color: hsl(var(--background));
}
```

- [ ] **Step 4: Wire tokens into tailwind.config.ts**

Replace the contents of `frontend/tailwind.config.ts` with:

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-geist-sans)", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        border: "hsl(var(--border))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        "accent-green": "hsl(var(--accent-green))",
        "accent-red": "hsl(var(--accent-red))",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 5: Apply fonts in the root layout**

Replace the contents of `frontend/app/layout.tsx` with:

```tsx
import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinScout",
  description:
    "Public markets research agent — tool use, RAG, and agentic Q&A over free financial data sources.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="bg-background font-sans text-foreground antialiased">{children}</body>
    </html>
  );
}
```

- [ ] **Step 6: Set the API base URL for local dev**

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 7: Verify the app builds**

Run: `cd frontend && npm run build`
Expected: build succeeds with no type errors.

- [ ] **Step 8: Commit**

```bash
cd d:/RAG/finscout
git add frontend
git commit -m "feat: scaffold Next.js frontend with dark fintech design tokens"
```

---

### Task 6: Design primitives and shared dependencies

**Files:**
- Create: `frontend/lib/utils.ts`
- Create: `frontend/components/ui/button.tsx`
- Create: `frontend/components/ui/input.tsx`
- Create: `frontend/components/ui/card.tsx`
- Create: `frontend/components/ui/badge.tsx`
- Modify: `frontend/tailwind.config.ts`

**Interfaces:**
- Produces: `cn(...)` utility; `<Button variant="default"|"outline" size="default"|"sm">`, `<Input>`, `<Card>`, `<Badge>` components; `prose`/`prose-invert` Tailwind Typography classes.
- Consumes: color/font tokens from Task 5.

Note: shadcn/ui's CLI (`npx shadcn init`) is interactive and won't work in a non-interactive shell, so these primitives are hand-authored following the same conventions (Radix-free, `cva` variants, `tailwind-merge`) shadcn itself uses.

- [ ] **Step 1: Install dependencies**

```bash
cd frontend && npm install clsx tailwind-merge class-variance-authority framer-motion react-markdown && npm install -D @tailwindcss/typography
```

- [ ] **Step 2: Add the typography plugin**

In `frontend/tailwind.config.ts`, change `plugins: []` to:

```ts
plugins: [require("@tailwindcss/typography")],
```

- [ ] **Step 3: Create the cn() utility**

Create `frontend/lib/utils.ts`:

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 4: Create Button**

Create `frontend/components/ui/button.tsx`:

```tsx
import { cva, type VariantProps } from "class-variance-authority";
import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-green",
  {
    variants: {
      variant: {
        default: "bg-accent-green text-black hover:bg-accent-green/90",
        outline: "border border-border bg-transparent text-foreground hover:bg-card",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 px-3 text-xs",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  )
);
Button.displayName = "Button";
```

- [ ] **Step 5: Create Input**

Create `frontend/components/ui/input.tsx`:

```tsx
import { InputHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-green",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
```

- [ ] **Step 6: Create Card and Badge**

Create `frontend/components/ui/card.tsx`:

```tsx
import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-lg border border-border bg-card p-4", className)} {...props} />;
}
```

Create `frontend/components/ui/badge.tsx`:

```tsx
import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-border px-2 py-0.5 font-mono text-xs text-muted-foreground",
        className
      )}
      {...props}
    />
  );
}
```

- [ ] **Step 7: Verify the app builds**

Run: `cd frontend && npm run build`
Expected: build succeeds with no type errors (primitives are unused so far — that's fine, no unused-var lint errors since they're exported).

- [ ] **Step 8: Commit**

```bash
cd d:/RAG/finscout
git add frontend
git commit -m "feat: add hand-authored shadcn-style UI primitives"
```

---

### Task 7: API client — SSE streaming + health check

**Files:**
- Create: `frontend/lib/api.ts`

**Interfaces:**
- Produces:
  - `type AskEvent = {type:"tool_call",tool:string,args:Record<string,unknown>} | {type:"tool_result",tool:string,result:unknown} | {type:"final",content:string} | {type:"error",detail:string}`
  - `type ResearchEvent = {type:"stage",stage:string,status:"start"|"done",result?:unknown} | {type:"final",markdown:string} | {type:"error",detail:string}`
  - `askStream(question: string): AsyncGenerator<AskEvent>`
  - `researchStream(ticker: string, company: string): AsyncGenerator<ResearchEvent>`
  - `checkHealth(): Promise<boolean>`
- Consumes: `NEXT_PUBLIC_API_URL` env var from Task 5; backend `/ask/stream`, `/research/stream`, `/health` from Task 4.

- [ ] **Step 1: Create the API client**

Create `frontend/lib/api.ts`:

```ts
export type AskEvent =
  | { type: "tool_call"; tool: string; args: Record<string, unknown> }
  | { type: "tool_result"; tool: string; result: unknown }
  | { type: "final"; content: string }
  | { type: "error"; detail: string };

export type ResearchEvent =
  | { type: "stage"; stage: string; status: "start" | "done"; result?: unknown }
  | { type: "final"; markdown: string }
  | { type: "error"; detail: string };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function* streamSSE<T>(path: string, body: unknown): AsyncGenerator<T> {
  const resp = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!resp.ok || !resp.body) {
    throw new Error(`request to ${path} failed: ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.split("\n").find((l) => l.startsWith("data: "));
      if (line) yield JSON.parse(line.slice("data: ".length)) as T;
    }
  }
}

export function askStream(question: string) {
  return streamSSE<AskEvent>("/ask/stream", { question });
}

export function researchStream(ticker: string, company: string) {
  return streamSSE<ResearchEvent>("/research/stream", { ticker, company });
}

export async function checkHealth(): Promise<boolean> {
  try {
    const resp = await fetch(`${API_URL}/health`, { cache: "no-store" });
    return resp.ok;
  } catch {
    return false;
  }
}
```

- [ ] **Step 2: Verify types compile**

Run: `cd frontend && npx tsc --noEmit`
Expected: no type errors.

- [ ] **Step 3: Commit**

```bash
cd d:/RAG/finscout
git add frontend/lib/api.ts
git commit -m "feat: add SSE streaming API client for ask/research endpoints"
```

---

### Task 8: Root nav with live backend health indicator

**Files:**
- Create: `frontend/components/nav.tsx`
- Modify: `frontend/app/layout.tsx`

**Interfaces:**
- Consumes: `checkHealth()` from Task 7, `cn()` from Task 6.
- Produces: `<Nav />` rendered in the root layout, with links to `/` and `/research`.

- [ ] **Step 1: Create the Nav component**

Create `frontend/components/nav.tsx`:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { checkHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Ask" },
  { href: "/research", label: "Research Brief" },
];

export function Nav() {
  const pathname = usePathname();
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const ok = await checkHealth();
      if (!cancelled) setHealthy(ok);
    };
    poll();
    const interval = setInterval(poll, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <nav className="flex items-center justify-between border-b border-border px-6 py-4">
      <div className="flex items-center gap-6">
        <span className="font-mono text-sm font-semibold tracking-tight text-accent-green">
          FinScout
        </span>
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "text-sm transition-colors hover:text-foreground",
              pathname === link.href ? "text-foreground" : "text-muted-foreground"
            )}
          >
            {link.label}
          </Link>
        ))}
      </div>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span
          className={cn(
            "h-2 w-2 rounded-full",
            healthy === null ? "bg-muted-foreground" : healthy ? "bg-accent-green" : "bg-accent-red"
          )}
        />
        {healthy === null ? "connecting…" : healthy ? "backend online" : "backend unreachable"}
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Render Nav in the root layout**

In `frontend/app/layout.tsx`, add the import:

```tsx
import { Nav } from "@/components/nav";
```

And change the `body` contents from `{children}` to:

```tsx
<body className="bg-background font-sans text-foreground antialiased">
  <Nav />
  {children}
</body>
```

- [ ] **Step 3: Verify the app builds**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
cd d:/RAG/finscout
git add frontend
git commit -m "feat: add nav with live backend health indicator"
```

---

### Task 9: Shared markdown panel + Ask (chat) page

**Files:**
- Create: `frontend/components/markdown-panel.tsx`
- Create: `frontend/components/chat/tool-step.tsx`
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `askStream(question)` and `AskEvent` from Task 7; `Button`, `Input` from Task 6.
- Produces: `<MarkdownPanel content={string} />` (reused by Task 11), `<ToolStep tool args done />`.

- [ ] **Step 1: Create MarkdownPanel**

Create `frontend/components/markdown-panel.tsx`:

```tsx
import ReactMarkdown from "react-markdown";

export function MarkdownPanel({ content }: { content: string }) {
  return (
    <div className="prose prose-invert prose-sm max-w-none rounded-md border border-border bg-card p-4">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
```

- [ ] **Step 2: Create ToolStep**

Create `frontend/components/chat/tool-step.tsx`:

```tsx
"use client";

import { motion } from "framer-motion";

export function ToolStep({
  tool,
  args,
  done,
}: {
  tool: string;
  args: Record<string, unknown>;
  done: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 font-mono text-xs text-muted-foreground"
    >
      <span className={`h-1.5 w-1.5 rounded-full bg-accent-green ${done ? "" : "animate-pulse"}`} />
      <span>
        {tool}({JSON.stringify(args)})
      </span>
      {done && <span className="ml-auto text-accent-green">done</span>}
    </motion.div>
  );
}
```

- [ ] **Step 3: Build the Ask page**

Replace the contents of `frontend/app/page.tsx` with:

```tsx
"use client";

import { useState } from "react";
import { askStream, type AskEvent } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ToolStep } from "@/components/chat/tool-step";
import { MarkdownPanel } from "@/components/markdown-panel";

type Step = { tool: string; args: Record<string, unknown>; done: boolean };

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function applyEvent(event: AskEvent) {
    if (event.type === "tool_call") {
      setSteps((prev) => [...prev, { tool: event.tool, args: event.args, done: false }]);
    } else if (event.type === "tool_result") {
      setSteps((prev) => {
        const next = [...prev];
        const idx = next.map((s) => s.done).lastIndexOf(false);
        if (idx !== -1) next[idx] = { ...next[idx], done: true };
        return next;
      });
    } else if (event.type === "final") {
      setAnswer(event.content);
    } else if (event.type === "error") {
      setError(event.detail);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || loading) return;

    setSteps([]);
    setAnswer(null);
    setError(null);
    setLoading(true);

    try {
      for await (const event of askStream(question)) {
        applyEvent(event);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-4 px-6 py-10">
      <h1 className="text-lg font-semibold">Ask FinScout</h1>
      <p className="text-sm text-muted-foreground">
        Open-ended research questions — the agent decides which tools to call.
      </p>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What's NVDA trading at, and what's its P/E?"
          disabled={loading}
        />
        <Button type="submit" disabled={loading}>
          {loading ? "Thinking…" : "Ask"}
        </Button>
      </form>

      <div className="flex flex-col gap-2">
        {steps.map((step, i) => (
          <ToolStep key={i} tool={step.tool} args={step.args} done={step.done} />
        ))}
      </div>

      {error && (
        <div className="rounded-md border border-accent-red/40 bg-accent-red/10 p-4 text-sm text-accent-red">
          {error}
        </div>
      )}

      {answer && <MarkdownPanel content={answer} />}
    </main>
  );
}
```

- [ ] **Step 4: Verify the app builds**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
cd d:/RAG/finscout
git add frontend
git commit -m "feat: build Ask chat page with live tool-call trace"
```

---

### Task 10: Research page — form + pipeline tracker + stat tiles

**Files:**
- Create: `frontend/components/research/pipeline-tracker.tsx`
- Create: `frontend/components/research/stat-tile.tsx`
- Create: `frontend/app/research/page.tsx`

**Interfaces:**
- Consumes: `researchStream(ticker, company)` and `ResearchEvent` from Task 7; `Button`, `Input` from Task 6; `MarkdownPanel` from Task 9.
- Produces: the `/research` route.

- [ ] **Step 1: Create PipelineTracker**

Create `frontend/components/research/pipeline-tracker.tsx`:

```tsx
"use client";

import { motion } from "framer-motion";

const STAGES = [
  { key: "market_data", label: "Market data" },
  { key: "news", label: "Recent news" },
  { key: "risk_factors", label: "Risk factors" },
  { key: "business_overview", label: "Business overview" },
];

export function PipelineTracker({ done }: { done: Set<string> }) {
  return (
    <div className="flex gap-3">
      {STAGES.map((stage) => {
        const isDone = done.has(stage.key);
        return (
          <motion.div
            key={stage.key}
            animate={{ opacity: isDone ? 1 : 0.5 }}
            className="flex flex-1 flex-col gap-1 rounded-md border border-border bg-card px-3 py-2"
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${isDone ? "bg-accent-green" : "bg-muted-foreground"}`}
            />
            <span className="font-mono text-xs text-muted-foreground">{stage.label}</span>
          </motion.div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Create StatTile**

Create `frontend/components/research/stat-tile.tsx`:

```tsx
export function StatTile({
  label,
  value,
  delta,
}: {
  label: string;
  value: string;
  delta?: "up" | "down";
}) {
  return (
    <div className="rounded-md border border-border bg-card p-3">
      <div className="font-mono text-xs text-muted-foreground">{label}</div>
      <div
        className={`font-mono text-lg font-semibold ${
          delta === "up" ? "text-accent-green" : delta === "down" ? "text-accent-red" : "text-foreground"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Build the Research page**

Create `frontend/app/research/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { researchStream, type ResearchEvent } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PipelineTracker } from "@/components/research/pipeline-tracker";
import { StatTile } from "@/components/research/stat-tile";
import { MarkdownPanel } from "@/components/markdown-panel";

type MarketData = {
  ticker: string;
  price?: number;
  currency?: string;
  market_cap?: number;
  pe_ratio?: number;
  fifty_two_week_high?: number;
  fifty_two_week_low?: number;
  sector?: string;
  error?: string;
};

export default function ResearchPage() {
  const [ticker, setTicker] = useState("");
  const [company, setCompany] = useState("");
  const [doneStages, setDoneStages] = useState<Set<string>>(new Set());
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function applyEvent(event: ResearchEvent) {
    if (event.type === "stage" && event.status === "done") {
      setDoneStages((prev) => new Set(prev).add(event.stage));
      if (event.stage === "market_data") setMarketData(event.result as MarketData);
    } else if (event.type === "final") {
      setMarkdown(event.markdown);
    } else if (event.type === "error") {
      setError(event.detail);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ticker.trim() || !company.trim() || loading) return;

    setDoneStages(new Set());
    setMarketData(null);
    setMarkdown(null);
    setError(null);
    setLoading(true);

    try {
      for await (const event of researchStream(ticker, company)) {
        applyEvent(event);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-10">
      <h1 className="text-lg font-semibold">Research Brief</h1>
      <p className="text-sm text-muted-foreground">
        Ticker + company in, a structured cited research brief out.
      </p>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="Ticker, e.g. AAPL"
          disabled={loading}
        />
        <Input
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          placeholder="Company, e.g. Apple Inc."
          disabled={loading}
        />
        <Button type="submit" disabled={loading}>
          {loading ? "Researching…" : "Generate"}
        </Button>
      </form>

      {(loading || doneStages.size > 0) && <PipelineTracker done={doneStages} />}

      {marketData && !marketData.error && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile
            label="Price"
            value={marketData.price ? `${marketData.price} ${marketData.currency ?? ""}` : "—"}
          />
          <StatTile label="P/E" value={marketData.pe_ratio ? String(marketData.pe_ratio) : "—"} />
          <StatTile
            label="Market cap"
            value={marketData.market_cap ? marketData.market_cap.toLocaleString() : "—"}
          />
          <StatTile
            label="52w range"
            value={
              marketData.fifty_two_week_low && marketData.fifty_two_week_high
                ? `${marketData.fifty_two_week_low}–${marketData.fifty_two_week_high}`
                : "—"
            }
          />
        </div>
      )}
      {marketData?.error && (
        <div className="rounded-md border border-accent-red/40 bg-accent-red/10 p-4 text-sm text-accent-red">
          {marketData.error}
        </div>
      )}

      {error && (
        <div className="rounded-md border border-accent-red/40 bg-accent-red/10 p-4 text-sm text-accent-red">
          {error}
        </div>
      )}

      {markdown && <MarkdownPanel content={markdown} />}
    </main>
  );
}
```

- [ ] **Step 4: Verify the app builds**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
cd d:/RAG/finscout
git add frontend
git commit -m "feat: build Research Brief page with pipeline tracker and stat tiles"
```

---

### Task 11: End-to-end manual verification

**Files:** none (verification only)

**Interfaces:** none

- [ ] **Step 1: Start the backend**

In one terminal, from `d:/RAG/finscout` with `GROQ_API_KEY` set and the venv active:

```bash
python -m uvicorn app.api.main:app --reload --port 8000
```

Expected: server starts, `http://localhost:8000/health` returns `{"status": "ok"}`.

- [ ] **Step 2: Start the frontend**

In a second terminal:

```bash
cd frontend && npm run dev
```

Expected: dev server starts on `http://localhost:3000`.

- [ ] **Step 3: Verify the nav health indicator**

Open `http://localhost:3000` in a browser. Confirm the nav shows "backend online" with a green dot within ~15s.

- [ ] **Step 4: Verify the Ask flow (golden path)**

On `/`, submit a real question (e.g. "What's NVDA trading at and what's its P/E?"). Confirm:
- Tool-call steps appear and animate in as they stream.
- Each step flips to "done" once its result arrives.
- The final answer renders as formatted markdown with source attribution.

- [ ] **Step 5: Verify the Research Brief flow (golden path)**

On `/research`, submit a real ticker + company (e.g. `NVDA` / `NVIDIA Corporation`). Confirm:
- The 4-stage pipeline tracker lights up stage-by-stage.
- Stat tiles populate with price/P/E/market cap/52-week range as soon as the market-data stage completes (before the full report finishes).
- The full structured brief (overview, financial snapshot, news, risks, sources) renders once done.

- [ ] **Step 6: Verify an error path**

On `/research`, submit an invalid ticker (e.g. `ZZZFAKE` / `Not A Real Company Inc.`) — mirroring the golden dataset's deliberate failure case. Confirm the market-data stage surfaces its `error` field plainly (not silently) while the rest of the pipeline still completes.

- [ ] **Step 7: Stop the backend and confirm the health indicator degrades gracefully**

Stop the `uvicorn` process, wait up to 15s. Confirm the nav dot turns red and reads "backend unreachable" instead of hanging or crashing the page.

- [ ] **Step 8: Report results**

No commit for this task — report back with a summary of what was verified (pass/fail per step above). If any step fails, file it as a follow-up fix before considering the frontend done.
