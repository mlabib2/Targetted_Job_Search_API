"""
Citadel Securities Scraper
Custom WordPress-based career page with AJAX loading
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import time
from typing import List, Dict
from datetime import datetime
import hashlib


class CitadelScraper:
    """Scraper for Citadel Securities careers page"""

    def __init__(self, headless: bool = True):
        self.base_url = "https://www.citadelsecurities.com/careers/open-opportunities/"
        self.headless = headless
        self.driver = None

    def _setup_driver(self):
        """Initialize Selenium WebDriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)

    def scrape_jobs(self, location_filter: str = "Hong Kong") -> List[Dict]:
        """
        Scrape all jobs from Citadel Securities

        Args:
            location_filter: Filter jobs by location (default: Hong Kong)

        Returns:
            List of job dictionaries
        """
        if not self.driver:
            self._setup_driver()

        jobs = []

        try:
            print(f"Loading Citadel Securities careers page...")
            self.driver.get(self.base_url)

            # Wait for jobs to load (AJAX)
            wait = WebDriverWait(self.driver, 15)

            # Try multiple possible selectors
            # Wait for page to fully load
            time.sleep(5)

            # Debug: Save page source to see structure
            print("Page loaded, searching for job listings...")

            # Try different possible selectors
            job_elements = []
            selectors = [
                (By.CLASS_NAME, "careers-position"),
                (By.CLASS_NAME, "job-listing"),
                (By.CLASS_NAME, "position"),
                (By.TAG_NAME, "article"),
                (By.CSS_SELECTOR, "[data-card-type='job']"),
                (By.CSS_SELECTOR, "a[href*='/careers/details/']"),
            ]

            for by, selector in selectors:
                try:
                    elements = self.driver.find_elements(by, selector)
                    if elements:
                        print(f"Found {len(elements)} elements with selector: {selector}")
                        job_elements = elements
                        break
                except:
                    continue

            # If still no elements, dump page source for debugging
            if not job_elements:
                print("\nNo job elements found. Saving page source for debugging...")
                with open("citadel_page_debug.html", "w") as f:
                    f.write(self.driver.page_source)
                print("Page source saved to citadel_page_debug.html")
                print("Page title:", self.driver.title)

            print(f"Found {len(job_elements)} total job listings")

            for job_elem in job_elements:
                try:
                    job_data = self._parse_job_element(job_elem)

                    # Filter by location if specified
                    if location_filter:
                        if location_filter.lower() in job_data.get('location', '').lower():
                            jobs.append(job_data)
                    else:
                        jobs.append(job_data)

                except Exception as e:
                    print(f"Error parsing job element: {e}")
                    continue

            print(f"Scraped {len(jobs)} jobs matching '{location_filter}'")

        except TimeoutException:
            print("Timeout waiting for page to load")
        except Exception as e:
            print(f"Error scraping Citadel: {e}")
        finally:
            if self.driver:
                self.driver.quit()

        return jobs

    def _parse_job_element(self, elem) -> Dict:
        """Parse individual job listing element"""

        # Extract title
        try:
            title_elem = elem.find_element(By.CLASS_NAME, "careers-position__title")
            title = title_elem.text.strip()
        except:
            title = "Unknown Title"

        # Extract URL
        try:
            link_elem = elem.find_element(By.TAG_NAME, "a")
            url = link_elem.get_attribute("href")
        except:
            url = self.base_url

        # Extract location(s)
        try:
            location_elem = elem.find_element(By.CLASS_NAME, "careers-position__location")
            location = location_elem.text.strip()
        except:
            location = "Unknown"

        # Extract department/category (if available)
        try:
            category_elem = elem.find_element(By.CLASS_NAME, "careers-position__category")
            department = category_elem.text.strip()
        except:
            department = None

        # Generate hash for deduplication
        job_hash = self._generate_hash(title, url)

        return {
            'title': title,
            'url': url,
            'location': location,
            'department': department,
            'description': None,  # Would need to visit individual page
            'posted_date': None,  # Not available on listing page
            'first_seen_at': datetime.now(),
            'job_hash': job_hash,
            'company': 'Citadel Securities'
        }

    def get_job_details(self, job_url: str) -> Dict:
        """
        Scrape detailed job description from individual job page

        Args:
            job_url: URL of the job posting

        Returns:
            Dictionary with detailed job info
        """
        if not self.driver:
            self._setup_driver()

        try:
            self.driver.get(job_url)
            wait = WebDriverWait(self.driver, 10)

            # Wait for job description to load
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "job-description")))

            # Extract full description
            try:
                desc_elem = self.driver.find_element(By.CLASS_NAME, "job-description")
                description = desc_elem.text.strip()
            except:
                description = None

            return {
                'description': description
            }

        except Exception as e:
            print(f"Error getting job details: {e}")
            return {}

    def _generate_hash(self, title: str, url: str) -> str:
        """Generate unique hash for job deduplication"""
        unique_string = f"citadel:{title.lower().strip()}:{url}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]

    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()


# Test/Demo
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Citadel Securities Scraper")
    print("=" * 60 + "\n")

    scraper = CitadelScraper(headless=False)  # Set to False to see browser

    # Scrape Hong Kong jobs
    hk_jobs = scraper.scrape_jobs(location_filter="Hong Kong")

    print(f"\n{'='*60}")
    print(f"Results: {len(hk_jobs)} Hong Kong jobs found")
    print(f"{'='*60}\n")

    # Display first 5 jobs
    for i, job in enumerate(hk_jobs[:5], 1):
        print(f"{i}. {job['title']}")
        print(f"   Location: {job['location']}")
        print(f"   Department: {job['department']}")
        print(f"   URL: {job['url'][:60]}...")
        print()

    scraper.close()
