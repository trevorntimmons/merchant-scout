"""Best-effort email discovery from a business's public website.

Only reads a business's own homepage/contact pages, checks robots.txt first,
and identifies itself via User-Agent. Does not scrape third-party sites.
"""
import re
import urllib.robotparser
from urllib.parse import urljoin, urlparse
from typing import Optional

import requests

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
CANDIDATE_PATHS = ["", "/contact", "/contact-us", "/about", "/about-us"]
HEADERS = {
    "User-Agent": (
        "MerchantScoutBot/1.0 (+https://github.com/; "
        "contact-info discovery, low-volume, respects robots.txt)"
    )
}
BAD_FRAGMENTS = ["example.com", "sentry.io", ".png", ".jpg", ".gif", "wixpress.com"]


def _allowed(base_url: str) -> bool:
    try:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(HEADERS["User-Agent"], base_url)
    except Exception:
        return True  # if robots.txt is unreachable, default to allow


def find_email(website: Optional[str], timeout: float = 6.0) -> Optional[str]:
    if not website:
        return None
    if not _allowed(website):
        return None

    for path in CANDIDATE_PATHS:
        url = urljoin(website, path)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            if resp.status_code != 200:
                continue
            match = EMAIL_RE.search(resp.text)
            if match:
                email = match.group(0)
                if not any(bad in email.lower() for bad in BAD_FRAGMENTS):
                    return email
        except requests.RequestException:
            continue
    return None
