"""Millennium Management scraper — Eightfold ATS at career.mlp.com."""

import requests
import time
from datetime import datetime, timezone
from typing import List, Dict


class MillenniumScraper:

    _LIST_URL   = "https://career.mlp.com/api/apply/v2/jobs"
    _DETAIL_URL = "https://career.mlp.com/api/apply/v2/jobs/{job_id}"
    _PAGE_SIZE  = 10   # Eightfold caps responses at 10 regardless of num

    def __init__(self, company_name: str):
        self.company_name = company_name
        self.board_token  = "mlp.com"   # used by scrape_all.py for logging

    def scrape_jobs(self, location_filter: str = "Hong Kong") -> List[Dict]:
        jobs   = []
        seen   = set()
        offset = 0

        while True:
            params = {
                "domain":   "mlp.com",
                "start":    offset,
                "num":      self._PAGE_SIZE,
                "location": location_filter,
            }
            resp = requests.get(self._LIST_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            positions = data.get("positions", [])
            if not positions:
                break

            for p in positions:
                loc = p.get("location", "")
                # Eightfold's location param is fuzzy — apply strict check
                if location_filter.lower() not in loc.lower():
                    continue
                job_id = p["id"]
                if job_id in seen:
                    break   # dedup guard against infinite loops
                seen.add(job_id)
                jobs.append(self._parse(p))

            total = data.get("count", 0)
            offset += len(positions)
            if offset >= total or len(positions) < self._PAGE_SIZE:
                break
            time.sleep(0.3)

        return jobs

    def get_job_details(self, job_id: int) -> Dict:
        resp = requests.get(
            self._DETAIL_URL.format(job_id=job_id),
            params={"domain": "mlp.com"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"description": data.get("job_description", "")}

    def _parse(self, raw: Dict) -> Dict:
        job_id = raw["id"]

        posted_date = None
        t_update = raw.get("t_update")
        if t_update:
            try:
                posted_date = datetime.fromtimestamp(int(t_update), tz=timezone.utc)
            except (ValueError, OSError):
                pass

        return {
            "title":       raw.get("name", "Unknown Title"),
            "url":         raw.get("canonicalPositionUrl",
                                   f"https://mlp.eightfold.ai/careers/job/{job_id}"),
            "location":    raw.get("location", "Hong Kong"),
            "job_type":    raw.get("type"),
            "posted_date": posted_date,
            "description": None,
            "company":     self.company_name,
            "eightfold_id": job_id,
        }
