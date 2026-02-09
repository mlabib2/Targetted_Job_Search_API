"""
Test database setup and operations
Run this to verify everything works
"""

from models.db import get_db
from datetime import datetime


def test_database():
    """Test all database operations"""

    print("=" * 60)
    print("Testing HK Job Monitor Database")
    print("=" * 60 + "\n")

    with get_db() as db:
        # Test 1: Add a company
        print("Test 1: Adding a company...")
        try:
            company_id = db.add_company(
                name="Test Company",
                career_url="https://testcompany.com/careers",
                ats_platform="Greenhouse",
                notes="This is a test"
            )
            print(f"✓ Company added with ID: {company_id}\n")
        except Exception as e:
            print(f"✗ Error: {e}\n")

        # Test 2: Get active companies
        print("Test 2: Retrieving active companies...")
        companies = db.get_active_companies()
        print(f"✓ Found {len(companies)} active companies")
        if companies:
            print(f"  First company: {companies[0]['name']}\n")

        # Test 3: Add a job
        print("Test 3: Adding a job...")
        if companies:
            job_id = db.add_job(
                company_id=companies[0]['id'],
                title="Senior Software Engineer - Trading Systems",
                url="https://testcompany.com/jobs/123",
                description="Build low-latency trading systems using C++ and Python",
                location="Hong Kong",
                job_type="Full-time"
            )
            if job_id:
                print(f"✓ New job added with ID: {job_id}\n")
            else:
                print("✓ Job already exists (deduplicated)\n")

        # Test 4: Add duplicate job (should be ignored)
        print("Test 4: Testing deduplication (adding same job again)...")
        if companies:
            duplicate_id = db.add_job(
                company_id=companies[0]['id'],
                title="Senior Software Engineer - Trading Systems",
                url="https://testcompany.com/jobs/123",
                description="Build low-latency trading systems using C++ and Python"
            )
            if duplicate_id is None:
                print("✓ Duplicate correctly detected and ignored\n")
            else:
                print("✗ Duplicate was not detected!\n")

        # Test 5: Update job match score
        print("Test 5: Updating job match score...")
        if job_id:
            db.update_job_match(
                job_id=job_id,
                match_score=0.85,
                match_reasons=["Python", "C++", "Trading", "Low-latency"]
            )
            print("✓ Match score updated to 85%\n")

        # Test 6: Get jobs to notify
        print("Test 6: Getting jobs that should trigger notifications...")
        jobs_to_notify = db.get_jobs_to_notify()
        print(f"✓ Found {len(jobs_to_notify)} jobs above threshold")
        for job in jobs_to_notify[:3]:  # Show first 3
            print(f"  - {job['title']} at {job['company']} ({job['match_score']:.0%} match)")
        print()

        # Test 7: Update profile
        print("Test 7: Updating user profile...")
        db.update_profile(
            cv_text="Sample CV text",
            skills=["Python", "C++", "Trading", "React", "Low-latency systems"],
            experience_years=2
        )
        profile = db.get_profile()
        print(f"✓ Profile updated with {len(profile['skills'])} skills")
        print(f"  Skills: {', '.join(profile['skills'][:5])}\n")

        # Test 8: Log scraper run
        print("Test 8: Logging scraper activity...")
        if companies:
            db.log_scrape(
                company_id=companies[0]['id'],
                status='success',
                jobs_found=15,
                new_jobs=3,
                duration=2.5
            )
            print("✓ Scraper log recorded\n")

        # Test 9: Get statistics
        print("Test 9: Getting database statistics...")
        stats = db.get_stats()
        print(f"✓ Statistics:")
        print(f"  Active companies: {stats['total_companies']}")
        print(f"  New jobs: {stats['new_jobs']}")
        print(f"  Matching jobs: {stats['matching_jobs']}")
        print()

        # Test 10: Mark job as notified
        print("Test 10: Marking job as notified...")
        if job_id:
            db.mark_job_notified(job_id)
            # Check if it's removed from notification queue
            jobs_to_notify_after = db.get_jobs_to_notify()
            print(f"✓ Job marked as notified")
            print(f"  Jobs to notify before: {len(jobs_to_notify)}")
            print(f"  Jobs to notify after: {len(jobs_to_notify_after)}\n")

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_database()
