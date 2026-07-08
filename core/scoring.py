"""Need-based opportunity scoring (1-100) with human-readable explanations.

The score measures how urgent an opportunity a merchant is -- not how big the
business is. Deal size (TPV) is computed separately in tpv.py so a rep can
weigh it on their own rather than have it baked into the priority order.
"""
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class ScoreResult:
    score: int
    explanation: List[str]
    dominant_signal: str


def _reviews_text(place: dict) -> List[str]:
    return [
        r.get("text", {}).get("text", "")
        for r in place.get("reviews", [])
        if r.get("text")
    ]


def score_merchant(place: dict, vertical, new_business_flag: bool) -> ScoreResult:
    points = 10  # floor
    explanation: List[str] = []
    signal_weights: Dict[str, int] = {}

    website = place.get("websiteUri")
    if not website:
        points += 20
        explanation.append(
            "+20 no website found — likely limited online ordering/payment presence"
        )
        signal_weights["no_website"] = 20

    reviews = _reviews_text(place)
    reviews_lower = [r.lower() for r in reviews]

    pain_hits = sum(1 for r in reviews_lower if any(k in r for k in vertical.pain_keywords))
    if pain_hits:
        pts = min(20, pain_hits * 7)
        points += pts
        explanation.append(
            f"+{pts} {pain_hits} review(s) mention possible payment/checkout friction"
        )
        signal_weights["pain_reviews"] = pts

    pos_mentions = sorted({kw for r in reviews_lower for kw in vertical.pos_keywords if kw in r})
    if pos_mentions:
        points += 10
        explanation.append(
            f"+10 review(s) mention current POS/processor: {', '.join(pos_mentions)}"
        )
        signal_weights["competitor_pos"] = 10

    rating = place.get("rating")
    review_count = place.get("userRatingCount", 0) or 0
    if rating is not None and rating < 3.5 and review_count >= 20:
        points += 10
        explanation.append(
            "+10 below-average rating with meaningful review volume — operational friction likely"
        )
        signal_weights["low_rating"] = 10

    if new_business_flag:
        points += 25
        explanation.append(
            "+25 appears to be a newly opened business — likely still shopping for a processor/POS"
        )
        signal_weights["new_business"] = 25

    score = max(1, min(100, points))
    dominant_signal = max(signal_weights, key=signal_weights.get) if signal_weights else "baseline"

    if not explanation:
        explanation.append("+10 baseline — no strong pain or opportunity signals found in public data")

    return ScoreResult(score=score, explanation=explanation, dominant_signal=dominant_signal)
