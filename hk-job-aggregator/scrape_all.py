"""
scrape_all.py — Scrape all Greenhouse companies and save to database

Usage:
    python scrape_all.py                  # scrape + fetch full descriptions
    python scrape_all.py --no-descriptions # scrape metadata only (faster)
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from scrapers.greenhouse_scraper import GreenhouseScraper
from models.db import get_db


# Greenhouse board tokens for known companies.
# Key must match the 'name' field in the companies table exactly.
GREENHOUSE_TOKENS = {
    # Confirmed working — sorted by HK job count
    'Jane Street':                      'janestreet',
    'Qube Research & Technologies':     'quberesearchandtechnologies',
    'Point72':                          'point72',
    'Squarepoint Capital':              'squarepointcapital',
    'Flow Traders':                     'flowtraders',
    'Jump Trading':                     'jumptrading',
    'Tower Research Capital':           'towerresearchcapital',
    'Schonfeld':                        'schonfeld',
    'IMC Trading':                      'imc',
    'Man Group':                        'mangroup',
    'WorldQuant':                       'worldquant',
    'Graham Capital Management':        'grahamcapitalmanagement',
    # Valid boards, currently 0 HK jobs but worth monitoring
    'AQR':                              'aqr',
    'Marshall Wace':                    'marshallwace',
    'Winton':                           'winton',
    'Akuna Capital':                    'akunacapital',
    'ExodusPoint':                      'exoduspoint',
    'PDT Partners':                     'pdtpartners',
}

LOCATION_FILTER = 'Hong Kong'
DESCRIPTION_DELAY = 0.3   # seconds between description API calls
COMPANY_DELAY = 1.0       # seconds between companies


def scrape_company(db, company: dict, fetch_descriptions: bool) -> dict:
    """
    Scrape one Greenhouse company and save jobs to DB.
    Returns a result dict summarising the run.
    """
    name = company['name']
    company_id = company['id']

    token = GREENHOUSE_TOKENS.get(name)
    if not token:
        return {
            'company': name,
            'status': 'skipped',
            'reason': 'no board token configured',
        }

    start = time.time()
    scraper = GreenhouseScraper(name, token)

    try:
        jobs = scraper.scrape_jobs(location_filter=LOCATION_FILTER)
    except Exception as e:
        duration = time.time() - start
        db.log_scrape(company_id, 'failed', error=str(e), duration=duration)
        return {'company': name, 'status': 'failed', 'error': str(e)}

    if not jobs:
        duration = time.time() - start
        db.update_company_scraped(company_id)
        db.log_scrape(company_id, 'no_jobs', jobs_found=0, new_jobs=0, duration=duration)
        return {'company': name, 'status': 'success', 'found': 0, 'new': 0, 'duplicates': 0}

    new_count = 0
    dupe_count = 0

    for job in jobs:
        job_id = db.add_job(
            company_id=company_id,
            title=job['title'],
            url=job['url'],
            location=job['location'],
            job_type=job.get('job_type'),
            posted_date=job.get('posted_date'),
        )

        if job_id is None:
            dupe_count += 1
            continue

        # New job — fetch full description if requested
        new_count += 1
        if fetch_descriptions and job.get('greenhouse_id'):
            try:
                details = scraper.get_job_details(job['greenhouse_id'])
                description = details.get('description')
                if description:
                    db.update_job_description(job_id, description)
                time.sleep(DESCRIPTION_DELAY)
            except Exception:
                pass  # description is optional, don't fail the whole job

    duration = time.time() - start
    db.update_company_scraped(company_id)
    db.log_scrape(
        company_id=company_id,
        status='success',
        jobs_found=len(jobs),
        new_jobs=new_count,
        duration=duration,
    )

    return {
        'company': name,
        'status': 'success',
        'found': len(jobs),
        'new': new_count,
        'duplicates': dupe_count,
        'duration': round(duration, 1),
    }


def scrape_all(fetch_descriptions: bool = True):
    print("=" * 60)
    print("HK Job Aggregator — Greenhouse Scraper")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

    results = []

    with get_db() as db:
        all_companies = db.get_active_companies()
        # Use GREENHOUSE_TOKENS as source of truth — ats_platform in DB is informational only
        company_by_name = {c['name']: c for c in all_companies}
        greenhouse_companies = [
            company_by_name[name]
            for name in GREENHOUSE_TOKENS
            if name in company_by_name
        ]
        missing = [name for name in GREENHOUSE_TOKENS if name not in company_by_name]
        if missing:
            print(f"Warning: not in DB (run seed): {missing}\n")

        print(f"Found {len(greenhouse_companies)} Greenhouse companies\n")

        for company in greenhouse_companies:
            print(f"→ {company['name']}")
            result = scrape_company(db, company, fetch_descriptions)
            results.append(result)

            if result['status'] == 'skipped':
                print(f"  ⊘ Skipped: {result['reason']}")
            elif result['status'] == 'failed':
                print(f"  ✗ Failed: {result.get('error', 'unknown error')}")
            else:
                desc_note = ' (+ descriptions)' if fetch_descriptions and result['new'] else ''
                print(
                    f"  ✓ {result['new']} new, "
                    f"{result['duplicates']} dupes, "
                    f"{result['found']} HK jobs found"
                    f"{desc_note} ({result.get('duration', 0)}s)"
                )

            time.sleep(COMPANY_DELAY)

        # ── Summary ─────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)

        total_new = sum(r.get('new', 0) for r in results if r['status'] == 'success')
        total_found = sum(r.get('found', 0) for r in results if r['status'] == 'success')
        failed = [r for r in results if r['status'] == 'failed']
        skipped = [r for r in results if r['status'] == 'skipped']

        for r in results:
            if r['status'] == 'success':
                sym = '✓'
                detail = f"{r['new']} new / {r['found']} HK jobs"
            elif r['status'] == 'skipped':
                sym = '⊘'
                detail = r['reason']
            else:
                sym = '✗'
                detail = 'FAILED'
            print(f"  {sym} {r['company']}: {detail}")

        print(f"\nTotal: {total_new} new jobs across {total_found} HK postings found")
        if failed:
            print(f"Failures ({len(failed)}): {[r['company'] for r in failed]}")
        if skipped:
            print(f"Skipped ({len(skipped)}): {[r['company'] for r in skipped]}")

        stats = db.get_stats()
        print(
            f"\nDatabase: {stats['new_jobs']} unscored new jobs, "
            f"{stats['total_companies']} active companies"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape all Greenhouse companies")
    parser.add_argument(
        '--no-descriptions',
        action='store_true',
        help='Skip fetching full job descriptions (faster, but needed for AI matching)',
    )
    args = parser.parse_args()

    scrape_all(fetch_descriptions=not args.no_descriptions)
