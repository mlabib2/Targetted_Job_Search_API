from abc import ABC, abstractmethod
from typing import List, Dict
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime


class BaseScraper(ABC):
    """Base class for all job board scrapers"""

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    @abstractmethod
    def scrape_listings(self, search_term: str = "", location: str = "Hong Kong") -> List[Dict]:
        """Scrape job listings from the source"""
        pass

    @abstractmethod
    def parse_job_detail(self, job_url: str) -> Dict:
        """Parse individual job details"""
        pass

    def generate_job_hash(self, title: str, company: str, posted_date: str) -> str:
        """Generate unique hash for deduplication"""
        unique_string = f"{title.lower().strip()}_{company.lower().strip()}_{posted_date}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def normalize_salary(self, salary_string: str) -> tuple:
        """Extract min and max salary from string"""
        # Implementation for parsing "HK$20,000 - HK$30,000" etc.
        if not salary_string:
            return None, None

        # Remove currency symbols and common words
        cleaned = salary_string.replace("HK$", "").replace("K", "000").replace(",", "")

        try:
            if "-" in cleaned or "to" in cleaned.lower():
                parts = cleaned.replace("to", "-").split("-")
                salary_min = float(parts[0].strip())
                salary_max = float(parts[1].strip()) if len(parts) > 1 else salary_min
                return salary_min, salary_max
            else:
                # Single value
                salary = float(cleaned.strip())
                return salary, salary
        except:
            return None, None

    def fetch_page(self, url: str) -> BeautifulSoup:
        """Fetch and parse a page"""
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
