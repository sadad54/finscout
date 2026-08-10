from unittest.mock import patch

from app.agent.research_flow import run_research, run_research_events


@patch("app.agent.research_flow.render_markdown")
@patch("app.agent.research_flow.generate_report")
@patch("app.agent.research_flow.search_filing_content")
@patch("app.agent.research_flow.get_recent_headlines")
@patch("app.agent.research_flow.get_market_snapshot")
def test_run_research_gathers_all_evidence_and_synthesizes(
    mock_market, mock_news, mock_filing, mock_generate, mock_render
):
    mock_market.return_value = {"ticker": "TSLA", "price": 250}
    mock_news.return_value = [{"title": "Tesla news"}]
    mock_filing.side_effect = [
        {"source_url": "url1", "excerpts": ["risk excerpt"]},
        {"source_url": "url1", "excerpts": ["overview excerpt"]},
    ]
    mock_generate.return_value = {"overview": "..."}
    mock_render.return_value = "# TSLA — Research Brief\n..."

    result = run_research("TSLA", "Tesla, Inc.")

    assert result == "# TSLA — Research Brief\n..."
    mock_market.assert_called_once_with("TSLA")
    mock_news.assert_called_once_with("TSLA")
    assert mock_filing.call_count == 2  # risk factors + business overview
    mock_generate.assert_called_once()


@patch("app.agent.research_flow.render_markdown")
@patch("app.agent.research_flow.generate_report")
@patch("app.agent.research_flow.search_filing_content")
@patch("app.agent.research_flow.get_recent_headlines")
@patch("app.agent.research_flow.get_market_snapshot")
def test_run_research_events_yields_stage_then_final(
    mock_market, mock_news, mock_filing, mock_generate, mock_render
):
    mock_market.return_value = {"ticker": "TSLA", "price": 250}
    mock_news.return_value = [{"title": "Tesla news"}]
    mock_filing.side_effect = [
        {"source_url": "url1", "excerpts": ["risk excerpt"]},
        {"source_url": "url1", "excerpts": ["overview excerpt"]},
    ]
    mock_generate.return_value = {"overview": "..."}
    mock_render.return_value = "# TSLA — Research Brief\n..."

    events = list(run_research_events("TSLA", "Tesla, Inc."))

    stage_names = [e["stage"] for e in events if e["type"] == "stage"]
    assert stage_names == [
        "market_data", "market_data",
        "news", "news",
        "risk_factors", "risk_factors",
        "business_overview", "business_overview",
    ]
    assert events[5] == {
        "type": "stage", "stage": "risk_factors", "status": "done",
        "result": {"source_url": "url1", "excerpts": ["risk excerpt"]},
    }
    assert events[-1] == {"type": "final", "markdown": "# TSLA — Research Brief\n..."}
    mock_market.assert_called_once_with("TSLA")
    assert mock_filing.call_count == 2