"""
Universal Lever Scraper
Works for any company using Lever ATS
"""

import requests
from typing import List, Dict
from datetime import datetime
import hashlib
import time


class LeverScraper:
    """Scraper for Lever-based career pages"""

    BASE_URL = "https://api.lever.co/v0/postings"

    def __init__(self, company_name: str, board_token: str):
        """
        Args:
            company_name: Display name (e.g., "Two Sigma")
            board_token: URL slug (e.g., "twosigma" from jobs.lever.co/twosigma)
        """
        self.company_name = company_name
        self.board_token = board_token
        self.api_url = f"{self.BASE_URL}/{board_token}"

    def scrape_jobs(self, location_filter: str = "Hong Kong") -> List[Dict]:
        """
        Scrape all jobs from Lever API.

        Args:
            location_filter: Filter jobs by location (case-insensitive substring match)

        Returns:
            List of job dictionaries
        """
        jobs = []

        try:
            print(f"Fetching jobs for {self.company_name} from Lever API...")
            print(f"URL: {self.api_url}?mode=json")

            response = requests.get(
                self.api_url,
                params={"mode": "json"},
                timeout=10,
            )
            response.raise_for_status()

            all_postings = response.json()
            print(f"Found {len(all_postings)} total jobs")

            for posting in all_postings:
                job = self._parse_posting(posting)

                if location_filter:
                    if location_filter.lower() in job["location"].lower():
                        jobs.append(job)
                else:
                    jobs.append(job)

            print(f"Scraped {len(jobs)} jobs matching '{location_filter}'")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching jobs: {e}")
        except Exception as e:
            print(f"Error parsing jobs: {e}")

        return jobs

    def _parse_posting(self, posting: Dict) -> Dict:
        """Parse a single Lever posting into the standard job dict."""
        lever_id = posting.get("id", "")
        title = posting.get("text", "Unknown Title")
        url = posting.get("hostedUrl", f"https://jobs.lever.co/{self.board_token}/{lever_id}")

        categories = posting.get("categories") or {}
        location = categories.get("location") or "Unknown"
        department = categories.get("team") or None
        job_type = categories.get("commitment") or None

        # createdAt is a Unix timestamp in milliseconds
        created_at_ms = posting.get("createdAt")
        posted_date = None
        if created_at_ms:
            try:
                posted_date = datetime.utcfromtimestamp(created_at_ms / 1000)
            except Exception:
                pass

        # descriptionPlain is available at list time (may be empty)
        description = posting.get("descriptionPlain") or None

        job_hash = self._generate_hash(title, url)

        return {
            "title": title,
            "url": url,
            "location": location,
            "department": department,
            "office": None,
            "job_type": job_type,
            "description": description,
            "posted_date": posted_date,
            "first_seen_at": datetime.now(),
            "job_hash": job_hash,
            "company": self.company_name,
            "lever_id": lever_id,
        }

    def get_job_details(self, job_id: str) -> Dict:
        """
        Get detailed job description from individual posting endpoint.

        Args:
            job_id: Lever posting ID (UUID string)

        Returns:
            Dict with description key
        """
        url = f"{self.BASE_URL}/{self.board_token}/{job_id}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            description = data.get("descriptionPlain") or data.get("description") or ""

            return {"description": description}

        except Exception as e:
            print(f"Error getting job details for {job_id}: {e}")
            return {}

    def _generate_hash(self, title: str, url: str) -> str:
        """Generate unique hash for job deduplication — same pattern as GreenhouseScraper."""
        unique_string = f"{self.company_name}:{title.lower().strip()}:{url}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]


# Known Lever board tokens for HK finance companies
LEVER_COMPANIES = {
    "Two Sigma":             "twosigma",
    "Hudson River Trading":  "hudsonrivertrading",
    "Millennium Management": "millennium",
    "Citadel":               "citadel",
}


# Test/Demo
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Lever Scraper")
    print("=" * 60 + "\n")

    for company_name, token in LEVER_COMPANIES.items():
        print(f"\nChecking {company_name} ({token})...")
        scraper = LeverScraper(company_name, token)
        jobs = scraper.scrape_jobs(location_filter="Hong Kong")
        print(f"  → {len(jobs)} Hong Kong jobs")
        for job in jobs[:3]:
            print(f"     • {job['title']} | {job['location']}")
