"""Revenue and TPV (Total Payment Volume) estimation.

Formula (vertical-adapted):
    estimated annual revenue  (benchmark bracket, adjusted by rating)
      x  % of revenue that's card-based   (vertical-specific)
      /  12
      = estimated monthly TPV
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class RevenueEstimate:
    annual_revenue: float
    confidence: str  # "High" | "Medium" | "Low"
    basis: str


@dataclass
class TPVEstimate:
    monthly_tpv: float
    est_transactions_per_month: float


def estimate_revenue(place: dict, vertical) -> RevenueEstimate:
    review_count = place.get("userRatingCount", 0) or 0
    rating = place.get("rating")
    price_level = place.get("priceLevel")

    bracket = vertical.revenue_benchmark[-1]
    for b in vertical.revenue_benchmark:
        if review_count <= b.max_reviews:
            bracket = b
            break

    base_revenue = bracket.annual_revenue

    rating_adj = 1.0
    if rating is not None:
        rating_adj = 1 + ((rating - 4.0) * 0.05)

    revenue = base_revenue * rating_adj

    if review_count >= 20 and rating is not None and price_level is not None:
        confidence = "High"
    elif review_count >= 5:
        confidence = "Medium"
    else:
        confidence = "Low"

    basis = (
        f"Benchmarked to {vertical.name} businesses with up to {bracket.max_reviews} reviews "
        f"(${bracket.annual_revenue:,.0f}/yr baseline), adjusted for a "
        f"{rating if rating is not None else 'unknown'}-star rating."
    )

    return RevenueEstimate(annual_revenue=revenue, confidence=confidence, basis=basis)


def estimate_tpv(revenue_estimate: RevenueEstimate, vertical) -> TPVEstimate:
    annual_card_volume = revenue_estimate.annual_revenue * vertical.card_payment_pct
    monthly_tpv = annual_card_volume / 12
    est_transactions = (
        monthly_tpv / vertical.avg_ticket_size if vertical.avg_ticket_size else 0
    )
    return TPVEstimate(monthly_tpv=monthly_tpv, est_transactions_per_month=est_transactions)
