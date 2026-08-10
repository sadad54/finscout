import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@patch("app.api.main.run_agent")
def test_ask_success(mock_run_agent):
    mock_run_agent.return_value = "NVDA is trading at $120."

    resp = client.post("/ask", json={"question": "What's NVDA trading at?"})

    assert resp.status_code == 200
    assert resp.json() == {"answer": "NVDA is trading at $120."}
    mock_run_agent.assert_called_once_with("What's NVDA trading at?")


def test_ask_rejects_empty_question():
    resp = client.post("/ask", json={"question": ""})
    assert resp.status_code == 422  # pydantic validation error, not our code


@patch("app.api.main.run_agent")
def test_ask_returns_502_on_agent_failure(mock_run_agent):
    mock_run_agent.side_effect = RuntimeError("Groq API down")

    resp = client.post("/ask", json={"question": "anything"})

    assert resp.status_code == 502
    assert "agent failed" in resp.json()["detail"]


@patch("app.api.main.run_research")
def test_research_success(mock_run_research):
    mock_run_research.return_value = "# TSLA — Research Brief\n..."

    resp = client.post("/research", json={"ticker": "tsla", "company": "Tesla, Inc."})

    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "TSLA"
    assert "Research Brief" in body["report_markdown"]
    mock_run_research.assert_called_once_with("tsla", "Tesla, Inc.")


@patch("app.api.main.run_research")
def test_research_returns_502_on_failure(mock_run_research):
    mock_run_research.side_effect = RuntimeError("EDGAR unreachable")

    resp = client.post("/research", json={"ticker": "TSLA", "company": "Tesla, Inc."})

    assert resp.status_code == 502


def test_cors_allows_frontend_origin():
    resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"


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