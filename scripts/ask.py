"""
scripts/ask.py - quick manual test harness for the agent loop.

Usage:
    python scripts/ask.py "What's Nvidia trading at and what's its P/E?"

Requires GROQ_API_KEY set in your environment (get a free key at
https://console.groq.com).
"""
import sys

from app.agent.orchestrator import run_agent

if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What's NVDA trading at?"
    print(run_agent(question, verbose=True))