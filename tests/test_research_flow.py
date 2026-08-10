from unittest.mock import patch

from app.agent.research_flow import run_research


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