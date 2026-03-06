"""Goldman Sachs scraper — uses the internal GraphQL API behind higher.gs.com."""

import time
import requests
from datetime import datetime
from typing import List, Dict, Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils import strip_html

_API = "https://api-higher.gs.com/gateway/api/v1/graphql"
_EXPERIENCES = ["PROFESSIONAL", "EARLY_CAREER", "CAMPUS"]
_PAGE_SIZE = 50

_QUERY = """
query RoleSearch($input: RoleSearchQueryInput!) {
  roleSearch(searchQueryInput: $input) {
    totalCount
    items {
      roleId
      jobTitle
      locations { city country }
      corporateTitle
      jobFunction
      lastPostedDate
      descriptionHtml
    }
  }
}
"""


class GoldmanScraper:

    def __init__(self, company_name: str = "Goldman Sachs"):
        self.company_name = company_name
        self.board_token = "goldman-graphql"  # for scrape_all.py logging

    def scrape_jobs(self, location_filter: str = "Hong Kong") -> List[Dict]:
        jobs = []
        page = 0

        while True:
            data = self._fetch_page(page)
            if data is None:
                break

            total = data["totalCount"]
            items = data["items"]
            if not items:
                break

            for item in items:
                locs = [f"{l.get('city') or ''}, {l.get('country') or ''}".strip(", ")
                        for l in item.get("locations", [])]
                location_str = " | ".join(locs) if locs else "Unknown"

                if location_filter and not any(
                    location_filter.lower() in loc.lower() for loc in locs
                ):
                    continue

                jobs.append(self._parse(item, location_str))

            page += 1
            if (page * _PAGE_SIZE) >= total:
                break

            time.sleep(0.5)  # avoid SSL connection drops from rapid pagination

        return jobs

    def get_job_details(self, role_id: str) -> Dict:
        # Description is already included in the search response
        return {}

    def _fetch_page(self, page: int) -> Optional[Dict]:
        for attempt in range(3):
            try:
                resp = requests.post(
                    _API,
                    json={
                        "query": _QUERY,
                        "variables": {
                            "input": {
                                "experiences": _EXPERIENCES,
                                "page": {"pageNumber": page, "pageSize": _PAGE_SIZE},
                            }
                        },
                    },
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    timeout=20,
                )
                resp.raise_for_status()
                result = resp.json()
                if "errors" in result:
                    print(f"GraphQL errors: {result['errors']}")
                    return None
                return result["data"]["roleSearch"]
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    print(f"Error fetching Goldman page {page}: {e}")
                    return None

    def _parse(self, item: Dict, location_str: str) -> Dict:
        role_id = item.get("roleId", "")
        posted_date = None
        raw_date = item.get("lastPostedDate")
        if raw_date:
            try:
                posted_date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
            except ValueError:
                pass

        return {
            "title": item.get("jobTitle", "Unknown Title"),
            "url": f"https://higher.gs.com/details/{role_id}",
            "location": location_str,
            "job_type": None,
            "posted_date": posted_date,
            "description": strip_html(item.get("descriptionHtml", "")),
            "company": self.company_name,
            "goldman_id": role_id,
        }
