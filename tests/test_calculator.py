from app.tools.calculator import market_cap_to_revenue, pct_change, price_to_earnings


def test_price_to_earnings():
    assert price_to_earnings(100, 5) == 20.0


def test_price_to_earnings_zero_eps():
    assert price_to_earnings(100, 0) is None


def test_market_cap_to_revenue():
    assert market_cap_to_revenue(1_000_000, 200_000) == 5.0


def test_pct_change_up():
    assert pct_change(50, 75) == 50.0


def test_pct_change_zero_old():
    assert pct_change(0, 75) is None