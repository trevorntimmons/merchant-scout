"""Rule-based best-acquisition-angle recommendation, keyed off the dominant scoring signal."""

ANGLES = {
    "new_business": (
        "Lead with ease of setup and no long-term contract — newly opened businesses "
        "are still shopping for a processor and haven't signed anything yet."
    ),
    "pain_reviews": (
        "Lead with reliability and lower processing fees — customers have flagged "
        "payment or checkout friction in reviews."
    ),
    "competitor_pos": (
        "Lead with a side-by-side rate/features comparison against their current "
        "processor — you know what they're using, so make the switch concrete."
    ),
    "low_rating": (
        "Lead with faster checkout and fewer declines — operational friction shows up "
        "in their reviews, and a smoother payment flow is a visible fix."
    ),
    "no_website": (
        "Lead with modern POS + online ordering — no digital presence found, this is a "
        "clear technology-gap sale."
    ),
    "baseline": (
        "No strong pain signal found publicly — lead with a general cost-savings "
        "statement audit to open the conversation."
    ),
}


def best_angle(dominant_signal: str) -> str:
    return ANGLES.get(dominant_signal, ANGLES["baseline"])
