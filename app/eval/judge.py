"""
judge.py — LLM-as-judge scoring for FinScout research briefs.

Why a judge model instead of exact-match checks: financial data changes
daily (prices, headlines), so a golden dataset can't pin an exact expected
answer without going stale within hours. Instead this scores each report
for whether it's faithful to the evidence actually retrieved for it —
reference-free evaluation is the standard approach for RAG systems for
exactly this reason.

Interview note: the judge uses a DIFFERENT model (Llama 3.1 8B) than the
report generator (Llama 3.3 70B). Using the same model to grade its own
output is a known failure mode (self-preference bias) — a different model,
even a smaller/cheaper one, is a low-cost way to reduce that.
"""
from __future__ import annotations

import json
import os

from groq import Groq

JUDGE_MODEL = "llama-3.1-8b-instant"

JUDGE_PROMPT = """You are grading a financial research brief for quality.
You will see the raw evidence it was supposed to be based on, and the
brief itself. Score it on three dimensions, each 0-5:

- faithfulness: are the claims in the brief actually supported by the
  evidence? Penalize any invented numbers, events, or facts not present
  in the evidence.
- completeness: does the brief meaningfully address overview, financial
  snapshot, news, and risk factors — or does it say "Not available" /
  skip sections that the evidence actually had data for?
- groundedness: does the brief cite sources appropriately for its claims?

Respond with ONLY a JSON object:
{"faithfulness": 0-5, "completeness": 0-5, "groundedness": 0-5, "reasoning": "one sentence explaining the scores"}"""


def judge_report(evidence: dict, report: dict) -> dict:
    """Score a generated report against the evidence it was built from.

    Returns {"faithfulness", "completeness", "groundedness", "reasoning"},
    or {"error": ...} if the judge's response wasn't valid JSON.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    user_content = (
        f"Evidence:\n{json.dumps(evidence, indent=2)}\n\n"
        f"Brief:\n{json.dumps(report, indent=2)}"
    )

    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"error": f"judge returned invalid JSON: {exc}", "raw": raw}