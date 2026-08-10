import json
from unittest.mock import MagicMock, patch

from app.eval.judge import judge_report


@patch("app.eval.judge.Groq")
def test_judge_report_parses_scores(mock_groq_cls, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_groq_cls.return_value = mock_client

    fake_score = {"faithfulness": 5, "completeness": 4, "groundedness": 5, "reasoning": "Well grounded."}
    message = MagicMock()
    message.content = json.dumps(fake_score)
    mock_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=message)])

    result = judge_report({"market_data": {}}, {"overview": "..."})

    assert result == fake_score


@patch("app.eval.judge.Groq")
def test_judge_report_handles_invalid_json(mock_groq_cls, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_groq_cls.return_value = mock_client

    message = MagicMock()
    message.content = "not json"
    mock_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=message)])

    result = judge_report({}, {})

    assert "error" in result