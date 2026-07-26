"""Workable ATS scraper — works for any company with a public Workable job board.

Public endpoint: https://apply.workable.com/api/v1/widget/accounts/{shortcode}
No per-job description endpoint found (tried /jobs/{shortcode} — 404), so
get_job_details() returns {} and descriptions are left unset, same as
Standard Chartered's titles-only pattern.
"""

import requests
from datetime import datetime
from typing import List, Dict


class WorkableScraper:

    def __init__(self, company_name: str, account_shortcode: str):
        self.company_name = company_name
        self.board_token = account_shortcode
        self._api = f"https://apply.workable.com/api/v1/widget/accounts/{account_shortcode}"

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

    def get_job_details(self, job_id: str) -> Dict:
        # No public per-job description endpoint found for Workable's widget API.
        return {}

    def _parse(self, raw: Dict) -> Dict:
        city = raw.get('city') or ''
        country = raw.get('country') or ''
        location = ', '.join(part for part in (city, country) if part) or 'Unknown'

        posted_date = None
        published_on = raw.get('published_on')
        if published_on:
            try:
                posted_date = datetime.fromisoformat(published_on)
            except ValueError:
                pass

        return {
            'title': raw.get('title', 'Unknown Title'),
            'url': raw.get('url', raw.get('shortlink', '')),
            'location': location,
            'job_type': raw.get('employment_type'),
            'posted_date': posted_date,
            'description': None,
            'company': self.company_name,
            'workable_id': raw.get('shortcode'),
        }
