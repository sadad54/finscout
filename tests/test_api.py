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