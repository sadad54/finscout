import json
from unittest.mock import MagicMock, patch

from app.agent.orchestrator import _run_tool, run_agent, run_agent_events


def _make_tool_call(call_id, name, arguments):
    call = MagicMock()
    call.id = call_id
    call.function.name = name
    call.function.arguments = json.dumps(arguments)
    return call


def test_run_tool_unknown_tool():
    result = _run_tool("not_a_real_tool", {})
    assert "error" in result


def test_run_tool_bad_arguments():
    # get_market_snapshot requires `ticker`, not `wrong_arg` -> TypeError -> caught
    result = _run_tool("get_market_snapshot", {"wrong_arg": "x"})
    assert "error" in result


@patch("app.agent.orchestrator.Groq")
def test_run_agent_calls_tool_then_answers(mock_groq_cls, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_groq_cls.return_value = mock_client

    # Turn 1: model asks to call get_market_snapshot
    tool_call = _make_tool_call("call_1", "get_market_snapshot", {"ticker": "NVDA"})
    first_message = MagicMock()
    first_message.tool_calls = [tool_call]
    first_message.model_dump.return_value = {"role": "assistant", "tool_calls": [tool_call]}
    first_response = MagicMock(choices=[MagicMock(message=first_message)])

    # Turn 2: model has the tool result and gives a final answer
    second_message = MagicMock()
    second_message.tool_calls = None
    second_message.content = "NVDA is trading at $120, per yfinance."
    second_response = MagicMock(choices=[MagicMock(message=second_message)])

    mock_client.chat.completions.create.side_effect = [first_response, second_response]

    with patch(
        "app.agent.orchestrator.get_market_snapshot",
        return_value={"ticker": "NVDA", "price": 120},
    ):
        answer = run_agent("What is NVDA trading at?")

    assert answer == "NVDA is trading at $120, per yfinance."
    assert mock_client.chat.completions.create.call_count == 2


@patch("app.agent.orchestrator.Groq")
def test_run_agent_stops_at_max_iterations(mock_groq_cls, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_groq_cls.return_value = mock_client

    # Model always wants another tool call - never terminates on its own.
    tool_call = _make_tool_call("call_x", "get_market_snapshot", {"ticker": "NVDA"})
    message = MagicMock()
    message.tool_calls = [tool_call]
    message.model_dump.return_value = {"role": "assistant", "tool_calls": [tool_call]}
    response = MagicMock(choices=[MagicMock(message=message)])
    mock_client.chat.completions.create.return_value = response

    with patch(
        "app.agent.orchestrator.get_market_snapshot",
        return_value={"ticker": "NVDA", "price": 120},
    ):
        answer = run_agent("loop forever")

    assert "maximum number of research steps" in answer
    assert mock_client.chat.completions.create.call_count == 6  # MAX_ITERATIONS


@patch("app.agent.orchestrator.Groq")
def test_run_agent_events_yields_tool_call_then_final(mock_groq_cls, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_groq_cls.return_value = mock_client

    tool_call = _make_tool_call("call_1", "get_market_snapshot", {"ticker": "NVDA"})
    first_message = MagicMock()
    first_message.tool_calls = [tool_call]
    first_message.model_dump.return_value = {"role": "assistant", "tool_calls": [tool_call]}
    first_response = MagicMock(choices=[MagicMock(message=first_message)])

    second_message = MagicMock()
    second_message.tool_calls = None
    second_message.content = "NVDA is trading at $120, per yfinance."
    second_response = MagicMock(choices=[MagicMock(message=second_message)])

    mock_client.chat.completions.create.side_effect = [first_response, second_response]

    with patch(
        "app.agent.orchestrator.get_market_snapshot",
        return_value={"ticker": "NVDA", "price": 120},
    ):
        events = list(run_agent_events("What is NVDA trading at?"))

    assert events[0] == {"type": "tool_call", "tool": "get_market_snapshot", "args": {"ticker": "NVDA"}}
    assert events[1] == {
        "type": "tool_result",
        "tool": "get_market_snapshot",
        "result": {"ticker": "NVDA", "price": 120},
    }
    assert events[2] == {"type": "final", "content": "NVDA is trading at $120, per yfinance."}