"""Load and represent vertical-specific scoring/TPV assumptions."""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

VERTICALS_DIR = Path(__file__).resolve().parent.parent / "verticals"


@dataclass
class RevenueBracket:
    max_reviews: int
    annual_revenue: float


@dataclass
class VerticalConfig:
    key: str
    name: str
    google_place_types: List[str]
    avg_ticket_size: float
    card_payment_pct: float
    revenue_benchmark: List[RevenueBracket]
    pos_keywords: List[str]
    pain_keywords: List[str]


def list_verticals() -> List[str]:
    return sorted(p.stem for p in VERTICALS_DIR.glob("*.json"))


def load_vertical(key: str) -> VerticalConfig:
    path = VERTICALS_DIR / f"{key}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No vertical config found for '{key}'. Available: {list_verticals()}"
        )
    data = json.loads(path.read_text())
    brackets = [RevenueBracket(**b) for b in data["revenue_benchmark"]]
    return VerticalConfig(
        key=key,
        name=data["name"],
        google_place_types=data["google_place_types"],
        avg_ticket_size=data["avg_ticket_size"],
        card_payment_pct=data["card_payment_pct"],
        revenue_benchmark=brackets,
        pos_keywords=[k.lower() for k in data.get("pos_keywords", [])],
        pain_keywords=[k.lower() for k in data.get("pain_keywords", [])],
    )
