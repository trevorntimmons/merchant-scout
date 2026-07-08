"""New-business detection -- the single strongest buying-intent signal in
merchant services. Two sources, both optional/best-effort:

1. A manual CSV dropped at data/new_business_registry.csv, exported from your
   state's open-data portal (most Secretaries of State publish new business
   filings). Expected columns: business_name,zip,registration_date.
2. A fallback proxy using the earliest Google review date as a rough "active
   since" estimate when no registry match is found (flagged low confidence).

To wire in a live state API instead of a manual CSV, implement `lookup()` here
and swap it into the pipeline in app.py.
"""
import csv
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional, Tuple

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "new_business_registry.csv"
NEW_BUSINESS_WINDOW_DAYS = 365


def _load_registry() -> List[dict]:
    if not REGISTRY_PATH.exists():
        return []
    with open(REGISTRY_PATH, newline="") as f:
        return list(csv.DictReader(f))


def _name_match(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _extract_zip(address: str) -> str:
    for token in address.split():
        cleaned = token.strip(",")
        if cleaned.isdigit() and len(cleaned) == 5:
            return cleaned
    return ""


def is_new_business(place: dict, registry: Optional[List[dict]] = None) -> Tuple[bool, str]:
    """Returns (is_new, basis_note)."""
    registry = registry if registry is not None else _load_registry()
    name = place.get("displayName", {}).get("text", "")
    zip_code = _extract_zip(place.get("formattedAddress", ""))

    for row in registry:
        if row.get("zip", "") == zip_code and _name_match(name, row.get("business_name", "")) > 0.8:
            try:
                reg_date = datetime.fromisoformat(row["registration_date"])
                if datetime.now() - reg_date <= timedelta(days=NEW_BUSINESS_WINDOW_DAYS):
                    return True, f"Matched state registry filing dated {row['registration_date']}"
            except (KeyError, ValueError):
                continue

    reviews = place.get("reviews", [])
    dates = [r.get("publishTime") for r in reviews if r.get("publishTime")]
    if dates:
        try:
            earliest = min(datetime.fromisoformat(d.replace("Z", "+00:00")) for d in dates)
            if datetime.now(earliest.tzinfo) - earliest <= timedelta(days=NEW_BUSINESS_WINDOW_DAYS):
                return True, "Proxy signal: earliest review is within the last 12 months (low confidence)"
        except ValueError:
            pass

    return False, ""
