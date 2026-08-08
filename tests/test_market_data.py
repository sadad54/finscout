from unittest.mock import MagicMock, patch

from app.tools.market_data import get_market_snapshot


@patch("app.tools.market_data.yf.Ticker")
def test_get_market_snapshot_success(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.info = {
        "currentPrice": 182.5,
        "currency": "USD",
        "marketCap": 2_800_000_000_000,
        "trailingPE": 31.2,
        "fiftyTwoWeekHigh": 199.6,
        "fiftyTwoWeekLow": 124.1,
        "sector": "Technology",
    }
    mock_ticker_cls.return_value = mock_ticker

    result = get_market_snapshot("aapl")

    assert result["ticker"] == "AAPL"  # confirms uppercasing/stripping
    assert result["price"] == 182.5
    assert result["sector"] == "Technology"
    assert "error" not in result


@patch("app.tools.market_data.yf.Ticker")
def test_get_market_snapshot_no_data(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.info = {}
    mock_ticker_cls.return_value = mock_ticker

    result = get_market_snapshot("FAKETICKER")

    assert "error" in result


@patch("app.tools.market_data.yf.Ticker")
def test_get_market_snapshot_raises(mock_ticker_cls):
    mock_ticker_cls.side_effect = ConnectionError("network down")

    result = get_market_snapshot("MSFT")

    assert "error" in result
    assert "network down" in result["error"]