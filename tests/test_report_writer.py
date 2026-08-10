import json
from unittest.mock import MagicMock, patch

from app.synthesis.report_writer import generate_report, render_markdown


@patch("app.synthesis.report_writer.Groq")
def test_generate_report_parses_json(mock_groq_cls, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_groq_cls.return_value = mock_client

    fake_report = {
        "overview": "Tesla designs and sells electric vehicles.",
        "financial_snapshot": "Trading at $250, P/E of 60.",
        "recent_news_summary": "Recent coverage of delivery numbers.",
        "risk_factors": ["Competition", "Supply chain"],
        "sources": ["yfinance", "SEC EDGAR filing"],
    }
    message = MagicMock()
    message.content = json.dumps(fake_report)
    mock_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=message)])

    result = generate_report("TSLA", "Tesla, Inc.", {"market_data": {}})

    assert result == fake_report


@patch("app.synthesis.report_writer.Groq")
def test_generate_report_handles_invalid_json(mock_groq_cls, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_groq_cls.return_value = mock_client

    message = MagicMock()
    message.content = "not valid json"
    mock_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=message)])

    result = generate_report("TSLA", "Tesla, Inc.", {})

    assert "error" in result


def test_render_markdown_success():
    report = {
        "overview": "Overview text.",
        "financial_snapshot": "Snapshot text.",
        "recent_news_summary": "News text.",
        "risk_factors": ["Risk A", "Risk B"],
        "sources": ["Source A"],
    }
    md = render_markdown("TSLA", report)
    assert "# TSLA — Research Brief" in md
    assert "- Risk A" in md
    assert "Overview text." in md


def test_render_markdown_error_report():
    md = render_markdown("TSLA", {"error": "invalid JSON"})
    assert "Report generation failed" in md