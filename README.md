# FinScout

Full-stack public-company research assistant: FastAPI, Next.js, Groq tool calling,
SEC filing retrieval, sentence-transformer embeddings and FAISS. Open-ended Q&A
uses a tool-selection loop; research briefs use a fixed evidence pipeline.
Both provide server-sent progress events and a final response.

## Run locally

Use Python 3.12 and Node.js 22. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Set GROQ_API_KEY and SEC_USER_AGENT in your environment.
uvicorn app.api.main:app --reload --port 8000
```

`SEC_USER_AGENT` should contain your application name and real contact email.
The default placeholder is unsuitable for live SEC requests. Embeddings download
on first use; live operation needs network access to the model host, Groq, SEC,
Yahoo Finance and news feeds. Provider failures or absent filings can leave
evidence incomplete. `/health` checks API liveness, not provider availability.

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000. `NEXT_PUBLIC_API_URL` defaults to
http://localhost:8000; backend `FRONTEND_ORIGIN` defaults to
http://localhost:3000. Set these before building when deploying elsewhere.

## Verification

```bash
python -m pytest tests/ -q
cd frontend
npm run build
```

CI tests the backend and builds the frontend. Tests mock external services; they
do not establish live market-data correctness or model quality. Whitespace-only
requests are rejected. Mid-stream provider errors are surfaced as error events,
and the browser now reports interrupted streams instead of silently stopping.

## Evaluation scope

The committed five-case [scorecard](eval_results/scorecard_20260810_201050.json)
reports model-judge averages of 4.2/5 faithfulness, 3.6/5 completeness and 3.4/5
groundedness. This is a small exploratory evaluation, not a reliable general
accuracy estimate or a new result from this readiness pass. Cases include an
invalid ticker and missing filing evidence. Source lists do not prove each claim
is supported; completeness and claim-level citation coverage remain limitations.
Run `python -m app.eval.run_eval` with working provider credentials to create a
new dated scorecard. Compare identical cases and evidence before claiming gains.

Readiness validation: 52 backend tests and three frontend SSE tests passed; production build passed. Run frontend checks with `node --test scripts/test-sse.mjs`.
