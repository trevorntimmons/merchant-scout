from core.scoring import score_merchant
from core.vertical_configs import RevenueBracket, VerticalConfig


def make_vertical():
    return VerticalConfig(
        key="test",
        name="Test Vertical",
        google_place_types=["restaurant"],
        avg_ticket_size=25,
        card_payment_pct=0.8,
        revenue_benchmark=[RevenueBracket(999999, 300000)],
        pos_keywords=["square"],
        pain_keywords=["declined", "cash only"],
    )


def test_baseline_score_no_signals():
    vertical = make_vertical()
    place = {"websiteUri": "https://example.com", "reviews": [], "rating": 4.5, "userRatingCount": 30}
    result = score_merchant(place, vertical, new_business_flag=False)
    assert result.score == 10
    assert result.dominant_signal == "baseline"


def test_no_website_adds_points():
    vertical = make_vertical()
    place = {"reviews": [], "rating": 4.5, "userRatingCount": 30}
    result = score_merchant(place, vertical, new_business_flag=False)
    assert result.score == 30
    assert result.dominant_signal == "no_website"


def test_new_business_is_dominant_signal():
    vertical = make_vertical()
    place = {"websiteUri": "https://example.com", "reviews": [], "rating": 4.5, "userRatingCount": 30}
    result = score_merchant(place, vertical, new_business_flag=True)
    assert result.dominant_signal == "new_business"
    assert result.score == 35


def test_pain_review_and_pos_mention_detected():
    vertical = make_vertical()
    place = {
        "websiteUri": "https://example.com",
        "reviews": [{"text": {"text": "The card was declined and their Square reader kept failing."}}],
        "rating": 4.5,
        "userRatingCount": 30,
    }
    result = score_merchant(place, vertical, new_business_flag=False)
    joined = " ".join(result.explanation).lower()
    assert "friction" in joined
    assert "square" in joined
    assert result.score > 10


def test_score_is_clamped_to_100():
    vertical = make_vertical()
    place = {
        "reviews": [{"text": {"text": "Cash only, card declined, Square broken."}}] * 5,
        "rating": 3.0,
        "userRatingCount": 50,
    }
    result = score_merchant(place, vertical, new_business_flag=True)
    assert result.score <= 100
