"""
Standard Chartered scraper — uses the public sitemap to discover HK jobs.

The career site (jobs.standardchartered.com) is J2W/SuccessFactors CSB and
fully JS-rendered, so there is no usable JSON API. However, the sitemap encodes
city, title, and job ID in each URL, letting us extract HK listings from one
single HTTP request.

Location filtering: job URLs begin with the city name. We only keep URLs
whose prefix matches a known Hong Kong district/location.
"""

import time
import html
import requests
import re
import urllib.parse
from typing import List, Dict, Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

_SITEMAP = "https://jobs.standardchartered.com/sitemap.xml"
_BASE = "https://jobs.standardchartered.com"

# Maps URL prefix → canonical location string.
# Keys are tested as startswith on the raw (XML-unescaped) slug.
_HK_PREFIXES: Dict[str, str] = {
    "Central-":    "Central, Hong Kong",
    "Kwun-Tong-":  "Kwun Tong, Hong Kong",
    "Quarry-Bay-": "Quarry Bay, Hong Kong",
    "Hong-Kong-":  "Hong Kong",
    "HK-":         "Hong Kong",
    "Admiralty-":  "Admiralty, Hong Kong",
    "Wan-Chai-":   "Wan Chai, Hong Kong",
    "Sheung-Wan-": "Sheung Wan, Hong Kong",
}


def _decode_slug(raw_slug: str) -> str:
    """URL-decode then HTML-unescape a sitemap slug."""
    return html.unescape(urllib.parse.unquote(raw_slug))


def _slug_to_title(slug: str, prefix: str) -> str:
    """Strip the location prefix from a slug and convert the rest to a title."""
    # prefix already confirmed to match (raw slug startswith prefix)
    body = slug[len(prefix):]
    # Commas appear as literal ',' (or '%2C' already decoded); dashes are word separators
    # Replace '-' with space but preserve commas and parentheses
    return body.replace("-", " ").strip()


class StandardCharteredScraper:

    def __init__(self, company_name: str = "Standard Chartered Hong Kong"):
        self.company_name = company_name
        self.board_token = "j2w-sitemap-scb"

    def scrape_jobs(self, location_filter: str = "Hong Kong") -> List[Dict]:
        raw = self._fetch_sitemap()
        if raw is None:
            return []
        return self._parse_sitemap(raw)

    def get_job_details(self, job_id: str) -> Dict:
        # The career site is fully JS-rendered; individual pages yield no
        # machine-readable description.  We can still pull a clean title from
        # the <meta name="description"> tag for the rare case where the slug
        # parse was messy — but we return no description body.
        return {"description": None}

    def _fetch_sitemap(self) -> Optional[str]:
        for attempt in range(3):
            try:
                resp = requests.get(
                    _SITEMAP,
                    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/xml,text/xml"},
                    timeout=20,
                )
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    print(f"Error fetching SCB sitemap: {e}")
                    return None

    def _parse_sitemap(self, xml: str) -> List[Dict]:
        jobs = []
        # Each entry: <loc>https://jobs.standardchartered.com/job/{slug}/{id}/</loc>
        pattern = re.compile(
            r"<loc>https://jobs\.standardchartered\.com/job/([^/]+)/(\d+)/</loc>"
        )
        for m in pattern.finditer(xml):
            raw_slug = m.group(1)    # still has %2C, &amp;, etc.
            job_id = m.group(2)
            full_url = f"{_BASE}/job/{raw_slug}/{job_id}/"

            # Detect HK prefix on the raw (XML-unescaped but still URL-encoded) slug.
            # We compare against URL-decoded slug because &amp; isn't in the prefix names.
            decoded_slug = _decode_slug(raw_slug)

            matched_prefix = None
            canonical_location = None
            for prefix, location in _HK_PREFIXES.items():
                if decoded_slug.startswith(prefix):
                    matched_prefix = prefix
                    canonical_location = location
                    break

            if matched_prefix is None:
                continue

            title = _slug_to_title(decoded_slug, matched_prefix)

            jobs.append({
                "title": title,
                "url": full_url,
                "location": canonical_location,
                "job_type": None,
                "posted_date": None,
                "description": None,
                "company": self.company_name,
                "scb_id": job_id,
            })

        return jobs
