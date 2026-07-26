"""Arrowpoint Investment Partners scraper — custom Framer-built careers page.

No ATS platform (Greenhouse/Workday/etc), no JSON API, no __NEXT_DATA__ or
JSON-LD block. Job links are plain <a href="./careers/{slug}">{Title}</a>
anchors in static HTML (confirmed — not JS-rendered), but per-job location
isn't reliably present near the link in the listing page. Given the firm is
a small (~6 open roles), Asia-focused (HK/SG/Dubai) fund, this scraper
ignores location_filter and returns everything — cheaper and more reliable
than fetching all 6 individual job pages to recover a location tag.
"""

import html
import re
import requests
from typing import List, Dict


class ArrowpointScraper:

    CAREERS_URL = "https://arrowpointfund.com/careers"

    def __init__(self, company_name: str):
        self.company_name = company_name
        self.board_token = "arrowpointfund-careers"

    def scrape_jobs(self, location_filter: str = "Hong Kong") -> List[Dict]:
        # location_filter intentionally ignored — see module docstring.
        try:
            resp = requests.get(self.CAREERS_URL, timeout=10)
            resp.raise_for_status()
            page_html = resp.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {self.company_name}: {e}")
            return []

        jobs = []
        seen_slugs = set()
        for m in re.finditer(r'<a[^>]*href="\./careers/([^"]+)"[^>]*>(.*?)</a>', page_html, re.S):
            slug, inner = m.groups()
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            title = re.sub(r'<[^>]+>', ' ', inner)
            title = re.sub(r'\s+', ' ', title).strip()
            title = html.unescape(title)
            if not title:
                continue
            jobs.append({
                'title': title,
                'url': f"https://arrowpointfund.com/careers/{slug}",
                'location': 'Hong Kong / Singapore / Dubai (unconfirmed per-role)',
                'job_type': None,
                'posted_date': None,
                'description': None,
                'company': self.company_name,
                'arrowpoint_slug': slug,
            })
        return jobs

    def get_job_details(self, slug: str) -> Dict:
        # Individual job pages are also Framer-rendered; not worth a second
        # fetch just for description text given the low job count.
        return {}
