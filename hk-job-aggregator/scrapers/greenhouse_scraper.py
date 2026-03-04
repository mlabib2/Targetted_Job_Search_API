"""Greenhouse ATS scraper — works for any company with a public Greenhouse board."""

import requests
from datetime import datetime
from typing import List, Dict


class GreenhouseScraper:

    def __init__(self, company_name: str, board_token: str):
        self.company_name = company_name
        self.board_token = board_token
        self._api = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"

    def scrape_jobs(self, location_filter: str = "Hong Kong") -> List[Dict]:
        try:
            resp = requests.get(self._api, timeout=10)
            resp.raise_for_status()
            all_jobs = resp.json().get('jobs', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {self.company_name}: {e}")
            return []

        jobs = []
        for raw in all_jobs:
            job = self._parse(raw)
            if not location_filter or location_filter.lower() in job['location'].lower():
                jobs.append(job)
        return jobs

    def get_job_details(self, job_id: int) -> Dict:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.board_token}/jobs/{job_id}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return {'description': resp.json().get('content', '')}
        except Exception as e:
            print(f"Error fetching job {job_id}: {e}")
            return {}

    def _parse(self, raw: Dict) -> Dict:
        job_id = raw.get('id')
        location_obj = raw.get('location')
        location = (
            location_obj.get('name', 'Unknown') if isinstance(location_obj, dict)
            else ('Remote' if location_obj is None else str(location_obj))
        )

        posted_date = None
        updated_at = raw.get('updated_at')
        if updated_at:
            try:
                posted_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except ValueError:
                pass

        job_type = None
        for meta in (raw.get('metadata') or []):
            if isinstance(meta, dict) and meta.get('name') == 'Employment Type':
                job_type = meta.get('value')

        return {
            'title': raw.get('title', 'Unknown Title'),
            'url': raw.get('absolute_url', f"https://boards.greenhouse.io/{self.board_token}/jobs/{job_id}"),
            'location': location,
            'job_type': job_type,
            'posted_date': posted_date,
            'description': None,
            'company': self.company_name,
            'greenhouse_id': job_id,
        }
