"""Environment/config loading for MerchantScout."""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    google_places_api_key: str
    anthropic_api_key: Optional[str]
    cache_ttl_hours: int


def get_settings() -> Settings:
    key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not key:
        raise RuntimeError(
            "GOOGLE_PLACES_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return Settings(
        google_places_api_key=key,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        cache_ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "24")),
    )
