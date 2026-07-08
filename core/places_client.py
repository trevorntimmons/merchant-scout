"""Google Places API (New) client with simple local JSON caching.

Uses a single searchText call per query with an expanded field mask, so
reviews/phone/website/rating all come back in one billed request rather than
a separate Place Details call per result.
"""
import hashlib
import json
import time
from pathlib import Path
from typing import List, Optional

import requests

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

SEARCH_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.internationalPhoneNumber",
        "places.websiteUri",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
        "places.businessStatus",
        "places.location",
        "places.reviews",
        "places.regularOpeningHours",
        "nextPageToken",
    ]
)


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(exist_ok=True, parents=True)
    h = hashlib.sha256(key.encode()).hexdigest()
    return CACHE_DIR / f"{h}.json"


def _cached(key: str, ttl_hours: int):
    path = _cache_path(key)
    if path.exists():
        age_hours = (time.time() - path.stat().st_mtime) / 3600
        if age_hours < ttl_hours:
            return json.loads(path.read_text())
    return None


def _store(key: str, data) -> None:
    _cache_path(key).write_text(json.dumps(data))


def search_merchants(
    api_key: str,
    query: str,
    location_bias: Optional[dict],
    max_results: int,
    ttl_hours: int = 24,
) -> List[dict]:
    """
    query: e.g. "restaurants in Denver, CO"
    location_bias: optional {"lat": .., "lng": .., "radius_meters": ..}
    Returns a list of raw place dicts (up to max_results, paginated).
    """
    cache_key = f"search::{query}::{location_bias}::{max_results}"
    cached = _cached(cache_key, ttl_hours)
    if cached is not None:
        return cached

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": SEARCH_FIELD_MASK,
    }
    body = {"textQuery": query, "pageSize": min(max_results, 20)}
    if location_bias:
        body["locationBias"] = {
            "circle": {
                "center": {
                    "latitude": location_bias["lat"],
                    "longitude": location_bias["lng"],
                },
                "radius": location_bias.get("radius_meters", 16000),
            }
        }

    results: List[dict] = []
    next_token = None
    while len(results) < max_results:
        if next_token:
            body["pageToken"] = next_token
            time.sleep(2)  # Google requires a short delay before a page token is valid
        resp = requests.post(SEARCH_URL, headers=headers, json=body, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("places", []))
        next_token = data.get("nextPageToken")
        if not next_token:
            break

    results = results[:max_results]
    _store(cache_key, results)
    return results
