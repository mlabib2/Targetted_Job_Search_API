"""Schroders scraper — Oracle HCM Cloud public CandidateExperience REST API."""

import time
import requests
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import quote

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils import strip_html

_BASE      = "https://ekbq.fa.em2.oraclecloud.com/hcmRestApi/resources/latest"
_SITE      = "CX_2"
_PAGE_SIZE = 25


class SchrodersScraper:

    def __init__(self, company_name: str = "Schroders"):
        self.company_name = company_name
        self.board_token  = "oracle-hcm-schroders"

    def scrape_jobs(self, location_filter: str = "London") -> List[Dict]:
        jobs   = []
        offset = 0

        while True:
            data = self._fetch_page(offset, location_filter)
            if data is None:
                break

            total = data.get("TotalJobsCount", 0)
            items = data.get("requisitionList", [])
            if not items:
                break

            for item in items:
                jobs.append(self._parse_listing(item))

            offset += _PAGE_SIZE
            if offset >= total:
                break

            time.sleep(0.5)

        return jobs

    def get_job_details(self, job_id: str) -> Dict:
        try:
            finder = f'ById;Id="{job_id}",siteNumber={_SITE}'
            url    = f"{_BASE}/recruitingCEJobRequisitionDetails?onlyData=true&finder={finder}"
            resp   = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                timeout=15,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                return {}
            job   = items[0]
            desc  = strip_html(job.get("ExternalDescriptionStr", ""))
            quals = strip_html(job.get("ExternalQualificationsStr", ""))
            resps = strip_html(job.get("ExternalResponsibilitiesStr", ""))
            parts = [p for p in [desc, quals, resps] if p]
            return {"description": "\n\n".join(parts) if parts else None}
        except Exception as e:
            print(f"Error fetching Schroders job {job_id}: {e}")
            return {}

    def _fetch_page(self, offset: int, location: str) -> Optional[Dict]:
        finder = f"findReqs;siteNumber={_SITE},location={quote(location)},offset={offset},limit={_PAGE_SIZE}"
        url    = f"{_BASE}/recruitingCEJobRequisitions?finder={finder}&onlyData=true&expand=requisitionList"
        for attempt in range(3):
            try:
                resp = requests.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                    timeout=20,
                )
                resp.raise_for_status()
                return resp.json()["items"][0]
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    print(f"Error fetching Schroders page offset={offset}: {e}")
                    return None

    def _parse_listing(self, item: Dict) -> Dict:
        job_id      = str(item.get("Id", ""))
        posted_date = None
        raw_date    = item.get("PostedDate")
        if raw_date:
            try:
                posted_date = datetime.fromisoformat(str(raw_date))
            except ValueError:
                pass

        return {
            "title":       item.get("Title", "Unknown Title"),
            "url":         f"https://ekbq.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/{_SITE}/jobs/preview/{job_id}",
            "location":    item.get("PrimaryLocation", "Unknown"),
            "job_type":    item.get("JobType"),
            "posted_date": posted_date,
            "description": None,
            "company":     self.company_name,
            "schroders_id": job_id,
        }
