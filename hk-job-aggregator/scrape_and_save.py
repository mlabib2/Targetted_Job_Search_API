"""
Scrape jobs and save to database
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from scrapers.greenhouse_scraper import GreenhouseScraper
from models.db import get_db


def scrape_jump_trading():
    """Scrape Jump Trading jobs and save to database"""

    print("=" * 60)
    print("Scraping Jump Trading via Greenhouse API")
    print("=" * 60 + "\n")

    # Initialize scraper
    scraper = GreenhouseScraper("Jump Trading", "jumptrading")

    # Scrape Hong Kong jobs
    jobs = scraper.scrape_jobs(location_filter="Hong Kong")

    print(f"\n{'='*60}")
    print(f"Found {len(jobs)} Hong Kong jobs")
    print(f"{'='*60}\n")

    if not jobs:
        print("No jobs to save!")
        return

    # Save to database
    with get_db() as db:
        # Find Jump Trading company in database
        companies = db.get_active_companies()
        jump_company = None

        for company in companies:
            if "jump" in company['name'].lower():
                jump_company = company
                break

        if not jump_company:
            print("Jump Trading not found in database. Adding it...")
            jump_company_id = db.add_company(
                name="Jump Trading",
                career_url="https://www.jumptrading.com/careers/",
                ats_platform="Greenhouse",
                notes="Greenhouse board token: jumptrading"
            )
        else:
            jump_company_id = jump_company['id']
            print(f"Found Jump Trading in database (ID: {jump_company_id})")

        # Save jobs
        new_jobs = 0
        duplicate_jobs = 0

        print(f"\nSaving jobs to database...")

        for job in jobs:
            # Try to add job (returns None if duplicate)
            job_id = db.add_job(
                company_id=jump_company_id,
                title=job['title'],
                url=job['url'],
                description=job.get('description'),
                location=job['location'],
                job_type=job.get('job_type'),
                posted_date=job.get('posted_date'),
                requirements=None
            )

            if job_id:
                new_jobs += 1
                print(f"  ✓ Added: {job['title'][:50]}")
            else:
                duplicate_jobs += 1
                print(f"  ⊘ Duplicate: {job['title'][:50]}")

        # Update company's last_scraped_at
        db.update_company_scraped(jump_company_id)

        # Log the scrape
        db.log_scrape(
            company_id=jump_company_id,
            status='success',
            jobs_found=len(jobs),
            new_jobs=new_jobs
        )

        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  New jobs saved: {new_jobs}")
        print(f"  Duplicates skipped: {duplicate_jobs}")
        print(f"  Total in database: {new_jobs + duplicate_jobs}")
        print(f"{'='*60}\n")

        # Show some stats
        stats = db.get_stats()
        print(f"Database Stats:")
        print(f"  Total companies: {stats['total_companies']}")
        print(f"  Total new jobs: {stats['new_jobs']}")
        print(f"  Matching jobs: {stats['matching_jobs']}")


def view_recent_jobs():
    """View recently added jobs from database"""

    print("\n" + "=" * 60)
    print("Recent Jobs in Database")
    print("=" * 60 + "\n")

    with get_db() as db:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Get recent jobs
        cursor.execute("""
            SELECT j.id, j.title, c.name as company, j.location,
                   j.posted_date, j.first_seen_at, j.url
            FROM jobs j
            JOIN companies c ON j.company_id = c.id
            ORDER BY j.first_seen_at DESC
            LIMIT 10
        """)

        jobs = cursor.fetchall()

        if not jobs:
            print("No jobs in database yet!")
            return

        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job[1]}")  # title
            print(f"   Company: {job[2]}")  # company
            print(f"   Location: {job[3]}")  # location
            if job[4]:  # posted_date
                print(f"   Posted: {job[4]}")
            print(f"   First seen: {job[5]}")
            print(f"   URL: {job[6][:70]}...")
            print()


if __name__ == "__main__":
    # Scrape and save
    scrape_jump_trading()

    # View what we saved
    view_recent_jobs()
