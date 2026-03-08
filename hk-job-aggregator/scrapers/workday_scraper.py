"""Workday ATS scraper — works for any company with a public Workday board."""

import re
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils import strip_html


class WorkdayScraper:

    def __init__(self, company_name: str, tenant: str, wd: str, site: str):
        self.company_name = company_name
        self.board_token = f"{tenant}/{site}"  # used by scrape_all.py for logging
        self._base = f"https://{tenant}.{wd}.myworkdayjobs.com"
        self._api = f"{self._base}/wday/cxs/{tenant}/{site}"
        self._site = site

    def scrape_jobs(self, location_filter: str = "Hong Kong") -> List[Dict]:
        jobs = []
        offset, limit = 0, 20
        total: Optional[int] = None

        while total is None or offset < total:
            try:
                data = self._fetch_page(offset, limit)
            except requests.exceptions.RequestException as e:
                print(f"Error fetching {self.company_name} (offset={offset}): {e}")
                break

            if total is None:
                total = data.get("total", 0)

            postings = data.get("jobPostings", [])
            if not postings:
                break

            for p in postings:
                job = self._parse(p)
                if not location_filter or location_filter.lower() in job["location"].lower():
                    jobs.append(job)

            offset += limit

        return jobs

    def get_job_details(self, external_path: str) -> Dict:
        try:
            resp = requests.get(
                f"{self._api}{external_path}",
                headers={"Accept": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            info = resp.json().get("jobPostingInfo", {})
            return {"description": strip_html(info.get("jobDescription", ""))}
        except Exception as e:
            print(f"Error fetching job details ({external_path}): {e}")
            return {}

    def _fetch_page(self, offset: int, limit: int) -> Dict:
        resp = requests.post(
            f"{self._api}/jobs",
            json={"limit": limit, "offset": offset, "searchText": "", "appliedFacets": {}},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def _parse(self, p: Dict) -> Dict:
        external_path = p.get("externalPath", "")
        title = p.get("title", "Unknown Title")
        url = f"{self._base}/{self._site}{external_path}"
        posted_date = self._parse_posted_on(p.get("postedOn", ""))

        return {
            "title": title,
            "url": url,
            "location": p.get("locationsText", "Unknown"),
            "job_type": None,
            "posted_date": posted_date,
            "description": None,
            "company": self.company_name,
            "workday_path": external_path,
        }

    @staticmethod
    def _parse_posted_on(text: str) -> Optional[datetime]:
        if not text:
            return None
        m = re.search(r'(\d+)\+?\s+[Dd]ay', text)
        if m:
            return datetime.now() - timedelta(days=int(m.group(1)))
        if "today" in text.lower() or "just" in text.lower():
            return datetime.now()
        return None
