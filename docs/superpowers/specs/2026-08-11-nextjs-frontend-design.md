# FinScout Next.js Frontend — Design

## Context

FinScout's backend (`app/`) is a FastAPI service with two research surfaces:

- `POST /ask` — open-ended Q&A. A hand-rolled Groq tool-calling loop
  (`app/agent/orchestrator.py`) picks which tools to call (market data,
  filings search, RAG filing search, news, calculator) and returns a final
  text answer.
- `POST /research` — fixed pipeline (`app/agent/research_flow.py`) that
  always gathers market data + news + risk/business filing excerpts, then
  synthesizes a structured, cited JSON report
  (`app/synthesis/report_writer.py`) rendered as markdown.
- `GET /health` — liveness check.

Today these are only reachable via `scripts/ask.py` or raw HTTP. This spec
covers building a Next.js frontend that makes both flows first-class,
interactive experiences, plus the backend streaming work needed to support
a live-progress UI.

## Goals

- Both `/ask` and `/research` are equally first-class UI surfaces.
- Dark, terminal-grade fintech visual identity — credible and data-dense,
  not gimmicky.
- Live progress while the agent/pipeline runs (tool calls, pipeline
  stages), not just a spinner.
- No regressions to existing Python tests, CLI (`scripts/ask.py`), or the
  eval harness (`app/eval/`), which all depend on `run_agent()` /
  `run_research()` keeping their current signatures.

## Non-goals

- Auth, multi-user accounts, persistence/history across sessions.
- Deployment/hosting setup (Vercel, Docker, etc.) — local dev only for now.
- Automated frontend test suite — this is a demo/portfolio project;
  verification is manual in-browser testing of both flows against the real
  backend, plus TypeScript strict mode + eslint as static checks.

## Backend changes (`app/`, `app/api/`)

### CORS

Add `CORSMiddleware` to `app/api/main.py`, allowing the frontend's origin
(`http://localhost:3000` by default, overridable via an env var) so the
browser can call FastAPI directly with no proxy layer.

### Streaming-capable agent/pipeline functions

`orchestrator.py` gains a generator, `run_agent_events(question)`, yielding
typed events as the loop runs:

```python
{"type": "tool_call", "tool": str, "args": dict}
{"type": "tool_result", "tool": str, "result": dict}
{"type": "final", "content": str}
```

`run_agent(question)` becomes a thin wrapper that drains
`run_agent_events` and returns just the final string. **Signature and
behavior unchanged** — existing callers (`scripts/ask.py`, eval harness,
`tests/test_api.py`'s mocked `run_agent`) keep working with no changes.

Same pattern in `research_flow.py`: `run_research_events(ticker, company)`
yields one event per evidence-gathering stage plus a final markdown event:

```python
{"type": "stage", "stage": "market_data", "status": "start" | "done", "result": dict | None}
{"type": "stage", "stage": "news", ...}
{"type": "stage", "stage": "risk_factors", ...}
{"type": "stage", "stage": "business_overview", ...}
{"type": "final", "markdown": str}
```

`run_research(ticker, company)` becomes the draining wrapper, same
signature as today.

### New streaming endpoints

`POST /ask/stream` and `POST /research/stream` in `app/api/main.py`, each
returning `StreamingResponse(media_type="text/event-stream")`. Each event
from the generator is formatted as an SSE frame: `data: {json}\n\n`. A
final `{"type": "error", "detail": ...}` event is emitted (not an HTTP
error) if the generator raises mid-stream, since the HTTP status is
already committed once streaming starts.

Existing `/ask` and `/research` are untouched — same request/response
shape, same error handling (502 on failure) as today.

### Testing

Extend `tests/test_api.py` with tests for the two new streaming endpoints:
mock the `_events` generators, assert the response is `text/event-stream`
and that emitted frames parse back to the expected event sequence. No
changes to existing tests.

## Frontend (`frontend/`, new Next.js app)

### Stack

- Next.js 14, App Router, TypeScript.
- Tailwind CSS.
- shadcn/ui (Radix-based primitives, owned in-repo) for form controls,
  cards, tabs, etc.
- Framer Motion for the streaming reveal / progress animations.
- `.env.local`: `NEXT_PUBLIC_API_URL` pointing at the FastAPI backend.

### Visual system

- Near-black background (`#0a0a0c` range), off-white text.
- Single accent color (electric green) used consistently for interactive
  elements and positive deltas; red reserved specifically for negative
  price/metric deltas — never used as a generic UI color.
- Geist Sans for UI text, Geist Mono for all numeric data (prices,
  tickers, ratios, dates) — reinforces the "data-dense terminal" feel.
- Subtle borders over heavy shadows; high information density.

### Pages

**`/` — Ask (chat)**

- Text input + submit for an open-ended question.
- On submit, opens the `/ask/stream` SSE connection. Tool calls stream in
  as small animated step cards (e.g. `Calling get_market_snapshot(AAPL)…`)
  that collapse into a compact result chip once resolved.
- Final answer streams/reveals as formatted markdown with source
  attribution matching the orchestrator's citation style (e.g. "per
  yfinance", "per the 2024 10-K").
- Errors (502, network failure) render as an inline error state in the
  chat thread, not a silent failure.

**`/research` — Research Brief**

- Form: ticker + company name.
- On submit, opens `/research/stream`. A 4-stage progress tracker
  (market data → news → risk factors → business overview) lights up
  stage-by-stage as events arrive.
- Finished report renders as a structured brief:
  - Stat-tile row for the financial snapshot (price, market cap, P/E,
    52-week range), with proper color use for deltas.
  - Overview card, recent-news list, risk-factors list, sources footer.
  - Copy-as-markdown affordance.
- Honors the backend's "honest failure" philosophy — e.g. the golden
  dataset's deliberately-invalid `ZZZFAKE` case — by rendering "no data
  found" states plainly rather than hiding or faking them.

Shared top nav switches between the two pages; a small live indicator
pings `/health` to show backend connectivity status.

### Data flow

`frontend/lib/api.ts` centralizes both:
- SSE streaming calls: `fetch()` + manual `ReadableStream` parsing of
  `data: {...}\n\n` frames into an async iterator (POST body support,
  unlike `EventSource` which is GET-only) — the standard pattern used by
  LLM streaming UIs.
- Plain JSON calls (`/health`).

### Verification

Run the Next.js dev server against the real FastAPI backend (`GROQ_API_KEY`
set) and manually exercise both the Ask and Research Brief flows in a
browser — golden-path and at least one error case (e.g. an invalid
ticker) — before considering the work complete. TypeScript strict mode and
eslint catch static issues; they don't substitute for this manual check.
