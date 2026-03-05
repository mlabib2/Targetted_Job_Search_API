"""Lever ATS scraper — works for any company with a public Lever board."""

import requests
from datetime import datetime
from typing import List, Dict


class LeverScraper:

    _API = "https://api.lever.co/v0/postings"

    def __init__(self, company_name: str, board_token: str):
        self.company_name = company_name
        self.board_token = board_token
        self._api_url = f"{self._API}/{board_token}"

    def scrape_jobs(self, location_filter: str = "Hong Kong") -> List[Dict]:
        try:
            resp = requests.get(self._api_url, params={"mode": "json"}, timeout=10)
            resp.raise_for_status()
            all_postings = resp.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {self.company_name}: {e}")
            return []

        jobs = []
        for raw in all_postings:
            job = self._parse(raw)
            if not location_filter or location_filter.lower() in job['location'].lower():
                jobs.append(job)
        return jobs

    def get_job_details(self, job_id: str) -> Dict:
        url = f"{self._API}/{self.board_token}/{job_id}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            description = data.get("descriptionPlain") or data.get("description") or ""
            return {"description": description}
        except Exception as e:
            print(f"Error fetching job {job_id}: {e}")
            return {}

    def _parse(self, raw: Dict) -> Dict:
        lever_id = raw.get("id", "")
        categories = raw.get("categories") or {}
        posted_date = None
        created_ms = raw.get("createdAt")
        if created_ms:
            try:
                posted_date = datetime.utcfromtimestamp(created_ms / 1000)
            except (OSError, ValueError):
                pass

        return {
            'title': raw.get("text", "Unknown Title"),
            'url': raw.get("hostedUrl", f"https://jobs.lever.co/{self.board_token}/{lever_id}"),
            'location': categories.get("location") or "Unknown",
            'job_type': categories.get("commitment"),
            'posted_date': posted_date,
            'description': raw.get("descriptionPlain"),
            'company': self.company_name,
            'lever_id': lever_id,
        }
