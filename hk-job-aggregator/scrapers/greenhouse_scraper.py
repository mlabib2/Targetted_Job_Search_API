"""
Universal Greenhouse Scraper
Works for any company using Greenhouse ATS
"""

import requests
from typing import List, Dict
from datetime import datetime
import hashlib
import time


class GreenhouseScraper:
    """Scraper for Greenhouse-based career pages"""

    def __init__(self, company_name: str, greenhouse_board_token: str):
        """
        Args:
            company_name: Display name (e.g., "Jump Trading")
            greenhouse_board_token: URL slug (e.g., "jumptrading" from boards.greenhouse.io/jumptrading)
        """
        self.company_name = company_name
        self.board_token = greenhouse_board_token
        self.api_url = f"https://boards-api.greenhouse.io/v1/boards/{greenhouse_board_token}/jobs"
        self.base_url = f"https://boards.greenhouse.io/{greenhouse_board_token}"

    def scrape_jobs(self, location_filter: str = "Hong Kong") -> List[Dict]:
        """
        Scrape all jobs from Greenhouse API

        Args:
            location_filter: Filter jobs by location (case-insensitive)

        Returns:
            List of job dictionaries
        """
        jobs = []

        try:
            print(f"Fetching jobs for {self.company_name} from Greenhouse API...")
            print(f"URL: {self.api_url}")

            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()

            data = response.json()
            all_jobs = data.get('jobs', [])

            print(f"Found {len(all_jobs)} total jobs")

            for job_data in all_jobs:
                job = self._parse_job(job_data)

                # Filter by location
                if location_filter:
                    if location_filter.lower() in job['location'].lower():
                        jobs.append(job)
                else:
                    jobs.append(job)

            print(f"Scraped {len(jobs)} jobs matching '{location_filter}'")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching jobs: {e}")
        except Exception as e:
            print(f"Error parsing jobs: {e}")

        return jobs

    def _parse_job(self, job_data: Dict) -> Dict:
        """Parse job data from Greenhouse API response"""

        # Extract basic info
        job_id = job_data.get('id')
        title = job_data.get('title', 'Unknown Title')

        # Location (can be None or dict)
        location_obj = job_data.get('location')
        if location_obj and isinstance(location_obj, dict):
            location = location_obj.get('name', 'Unknown')
        else:
            location = 'Remote' if location_obj is None else str(location_obj)

        # URL
        url = job_data.get('absolute_url', f"{self.base_url}/jobs/{job_id}")

        # Departments (may not exist in API response)
        departments = job_data.get('departments') or []
        department = departments[0].get('name') if departments else None

        # Offices (may not exist in API response)
        offices = job_data.get('offices') or []
        office = offices[0].get('name') if offices else None

        # Job type (if available)
        metadata = job_data.get('metadata') or []
        job_type = None
        if metadata:
            for meta in metadata:
                if isinstance(meta, dict) and meta.get('name') == 'Employment Type':
                    job_type = meta.get('value')

        # Posted date (if available in updated_at)
        updated_at = job_data.get('updated_at')
        posted_date = None
        if updated_at:
            try:
                # Parse ISO format: "2024-01-15T12:00:00Z"
                posted_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except:
                pass

        # Generate hash
        job_hash = self._generate_hash(title, url)

        return {
            'title': title,
            'url': url,
            'location': location,
            'department': department,
            'office': office,
            'job_type': job_type,
            'description': None,  # Would need to fetch individual job page
            'posted_date': posted_date,
            'first_seen_at': datetime.now(),
            'job_hash': job_hash,
            'company': self.company_name,
            'greenhouse_id': job_id
        }

    def get_job_details(self, job_id: int) -> Dict:
        """
        Get detailed job description from individual job endpoint

        Args:
            job_id: Greenhouse job ID

        Returns:
            Dict with job description and requirements
        """
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.board_token}/jobs/{job_id}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            description = data.get('content', '')

            return {
                'description': description
            }

        except Exception as e:
            print(f"Error getting job details: {e}")
            return {}

    def _generate_hash(self, title: str, url: str) -> str:
        """Generate unique hash for job deduplication"""
        unique_string = f"{self.company_name}:{title.lower().strip()}:{url}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]


# Known Greenhouse board tokens for HK finance companies
GREENHOUSE_COMPANIES = {
    'Jump Trading': 'jumptrading',
    'DRW': 'drw',
    'Citadel': 'citadel',  # May use custom page, but worth trying
}


# Test/Demo
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Greenhouse Scraper")
    print("=" * 60 + "\n")

    # Test with Jump Trading
    company = "Jump Trading"
    board_token = "jumptrading"

    scraper = GreenhouseScraper(company, board_token)
    jobs = scraper.scrape_jobs(location_filter="Hong Kong")

    print(f"\n{'='*60}")
    print(f"Results: {len(jobs)} Hong Kong jobs at {company}")
    print(f"{'='*60}\n")

    # Display jobs
    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job['title']}")
        print(f"   Location: {job['location']}")
        print(f"   Department: {job['department']}")
        if job['posted_date']:
            print(f"   Posted: {job['posted_date'].strftime('%Y-%m-%d')}")
        print(f"   URL: {job['url']}")
        print()

    # Try other companies
    print("\n" + "="*60)
    print("Testing other Greenhouse companies...")
    print("="*60 + "\n")

    for company_name, token in GREENHOUSE_COMPANIES.items():
        if company_name == "Jump Trading":
            continue  # Already tested

        print(f"\nChecking {company_name}...")
        scraper = GreenhouseScraper(company_name, token)
        jobs = scraper.scrape_jobs(location_filter="")
        print(f"  → {len(jobs)} total jobs")

        hk_jobs = [j for j in jobs if 'hong kong' in j['location'].lower()]
        print(f"  → {len(hk_jobs)} Hong Kong jobs")
