from core.tpv import estimate_revenue, estimate_tpv
from core.vertical_configs import RevenueBracket, VerticalConfig


def make_vertical():
    return VerticalConfig(
        key="test",
        name="Test Vertical",
        google_place_types=["restaurant"],
        avg_ticket_size=25,
        card_payment_pct=0.8,
        revenue_benchmark=[RevenueBracket(50, 300000), RevenueBracket(999999, 900000)],
        pos_keywords=["square"],
        pain_keywords=["declined"],
    )


def test_estimate_revenue_low_confidence_small_business():
    vertical = make_vertical()
    place = {"userRatingCount": 2}
    result = estimate_revenue(place, vertical)
    assert result.annual_revenue == 300000
    assert result.confidence == "Low"


def test_estimate_revenue_high_confidence_with_rating():
    vertical = make_vertical()
    place = {"userRatingCount": 40, "rating": 4.5, "priceLevel": "MODERATE"}
    result = estimate_revenue(place, vertical)
    assert result.confidence == "High"
    assert result.annual_revenue > 300000  # rating above 4.0 bumps it up


def test_estimate_tpv_matches_formula():
    vertical = make_vertical()
    place = {"userRatingCount": 100, "rating": 4.0}
    revenue_est = estimate_revenue(place, vertical)
    tpv = estimate_tpv(revenue_est, vertical)
    expected_monthly = (revenue_est.annual_revenue * vertical.card_payment_pct) / 12
    assert abs(tpv.monthly_tpv - expected_monthly) < 0.01
