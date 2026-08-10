"""
run_eval.py — runs the golden dataset through the full pipeline, scores
each report with the LLM judge, and writes a scorecard.

Run this after any change to a prompt, model, or retrieval parameter to
check whether quality moved up or down — this is the "measure it, don't
just eyeball it" answer to the JD's "testing, iteration, and continuous
improvement" bullet. Diffing two scorecards' avg_faithfulness before/after
a prompt change is a concrete regression check, not a vibe check.

Usage:
    python -m app.eval.run_eval
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.agent.research_flow import gather_evidence_and_report
from app.eval.golden_dataset import GOLDEN_CASES
from app.eval.judge import judge_report

SCORECARD_DIR = Path("eval_results")


def run_eval() -> dict:
    """Run every golden case, score it, and return a summary scorecard."""
    results = []
    for case in GOLDEN_CASES:
        evidence, report = gather_evidence_and_report(case["ticker"], case["company"])
        score = judge_report(evidence, report)
        results.append({"ticker": case["ticker"], "score": score})

    valid_scores = [r["score"] for r in results if "error" not in r["score"]]
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "num_cases": len(GOLDEN_CASES),
        "num_scored": len(valid_scores),
        "avg_faithfulness": _avg(valid_scores, "faithfulness"),
        "avg_completeness": _avg(valid_scores, "completeness"),
        "avg_groundedness": _avg(valid_scores, "groundedness"),
        "results": results,
    }

    SCORECARD_DIR.mkdir(exist_ok=True)
    out_path = SCORECARD_DIR / f"scorecard_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"Scorecard written to {out_path}")
    print(
        f"avg faithfulness={summary['avg_faithfulness']}, "
        f"completeness={summary['avg_completeness']}, "
        f"groundedness={summary['avg_groundedness']}"
    )
    return summary


def _avg(scores: list[dict], key: str) -> float | None:
    values = [s[key] for s in scores if key in s]
    return round(sum(values) / len(values), 2) if values else None


if __name__ == "__main__":
    run_eval()