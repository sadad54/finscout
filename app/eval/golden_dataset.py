"""
golden_dataset.py — the test set for the eval harness.

Deliberately NOT a set of fixed expected answers — stock prices and news
change daily, so exact-match golden answers would go stale within hours.
Instead this is a set of representative test cases: real, well-known
companies to check the happy path, plus one deliberately invalid ticker to
check graceful failure handling. run_eval.py runs each case through the
full pipeline and scores the OUTPUT against its OWN retrieved evidence
(see judge.py) rather than against a fixed answer — the standard
reference-free approach for evaluating RAG systems.
"""
from __future__ import annotations

GOLDEN_CASES = [
    {"ticker": "AAPL", "company": "Apple Inc."},
    {"ticker": "TSLA", "company": "Tesla, Inc."},
    {"ticker": "MSFT", "company": "Microsoft Corporation"},
    {"ticker": "NVDA", "company": "NVIDIA Corporation"},
    # Deliberately invalid ticker/company: a good report honestly says "no
    # data found"; a bad one hallucinates plausible-sounding numbers for a
    # company that doesn't exist. The judge should catch the difference.
    {"ticker": "ZZZFAKE", "company": "Not A Real Company Inc."},
]