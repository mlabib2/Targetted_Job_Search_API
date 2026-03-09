"""
scrape_all.py — Scrape all Greenhouse companies and save to database

Usage:
    python scrape_all.py                  # scrape + fetch full descriptions
    python scrape_all.py --no-descriptions # scrape metadata only (faster)
"""

import sys
import os
import time
import argparse
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from scrapers.greenhouse_scraper import GreenhouseScraper
from scrapers.lever_scraper import LeverScraper
from scrapers.workday_scraper import WorkdayScraper
from scrapers.goldman_scraper import GoldmanScraper
from scrapers.jpmorgan_scraper import JPMorganScraper
from models.db import get_db

# GitHub Actions log helpers
CI = os.getenv("GITHUB_ACTIONS") == "true"

def ts():
    return datetime.utcnow().strftime("%H:%M:%S")

def log(msg):
    print(f"[{ts()}] {msg}", flush=True)

def group(name):
    if CI:
        print(f"::group::{name}", flush=True)
    else:
        print(f"\n── {name}", flush=True)

def endgroup():
    if CI:
        print("::endgroup::", flush=True)

def warn(msg):
    if CI:
        print(f"::warning::{msg}", flush=True)
    else:
        print(f"  ⚠ {msg}", flush=True)

def error(msg):
    if CI:
        print(f"::error::{msg}", flush=True)
    else:
        print(f"  ✗ {msg}", flush=True)


# Board tokens for known companies.
# Keys must match the 'name' field in the companies table exactly.
GREENHOUSE_TOKENS = {
    # Confirmed working — sorted by HK job count (verified May 2026)
    'Qube Research & Technologies':     'quberesearchandtechnologies',  # 24 HK jobs
    'Jane Street':                      'janestreet',                    # 17 HK jobs
    'Point72':                          'point72',                       # 9 HK jobs
    'Squarepoint Capital':              'squarepointcapital',            # 9 HK jobs
    'Tower Research Capital':           'towerresearchcapital',          # 7 HK jobs
    'Flow Traders':                     'flowtraders',                   # 6 HK jobs
    'Schonfeld':                        'schonfeld',                     # 6 HK jobs
    'Jump Trading':                     'jumptrading',                   # 4 HK jobs
    'IMC Trading':                      'imc',                           # 2 HK jobs
    'Man Group':                        'mangroup',                      # 2 HK jobs
    'WorldQuant':                       'worldquant',                    # 1 HK job
    'DRW':                              'drweng',                        # 1 HK job
    'Hudson River Trading':             'wehrtyou',                      # 1 HK job
    'Optiver':                          'optiverus',                     # 3 HK jobs confirmed May 2026
    'Virtu Financial':                  'virtu',                         # 2 HK jobs confirmed May 2026
}

LEVER_TOKENS = {
    # NOTE: Citadel (hedge fund) API returns 404 — board may be private, pending investigation
    # Removed: Two Sigma (custom site careers.twosigma.com, not Lever)
    # Removed: Millennium Management (uses Eightfold at career.mlp.com, not Lever)
    # Removed: Hudson River Trading (moved to Greenhouse above, token: wehrtyou)
    # Removed: Optiver (uses Greenhouse, token: optiverus)
    # Removed: Virtu Financial (uses Greenhouse, token: virtu)
}

# Workday companies: name must match the DB 'name' column exactly (from seed_companies.py)
# Config: tenant, wd (data center), site (board name)
WORKDAY_TOKENS = {
    'Morgan Stanley Hong Kong': {'tenant': 'ms',         'wd': 'wd5', 'site': 'External'},
    'Barclays Hong Kong':       {'tenant': 'barclays',   'wd': 'wd3', 'site': 'External_Career_Site_Barclays'},
    'Deutsche Bank':            {'tenant': 'db',         'wd': 'wd3', 'site': 'DBWebsite'},
    'Macquarie':                {'tenant': 'mq',         'wd': 'wd3', 'site': 'CareersatMQ'},
    'BlackRock':                {'tenant': 'blackrock',  'wd': 'wd1', 'site': 'BlackRock_Professional'},
    'HKEX':                     {'tenant': 'hkex',       'wd': 'wd3', 'site': 'HKEXCareerPage'},
    'Fidelity International':   {'tenant': 'fil',        'wd': 'wd3', 'site': '001'},
    'State Street':             {'tenant': 'statestreet','wd': 'wd1', 'site': 'Global'},
}

# Goldman Sachs uses a custom GraphQL scraper — no token needed
GOLDMAN_COMPANIES = ['Goldman Sachs Hong Kong']

# JPMorgan uses Oracle HCM Cloud public REST API — no token needed
JPMORGAN_COMPANIES = ['JPMorgan Chase Hong Kong']

LOCATION_FILTER = 'Hong Kong'
DESCRIPTION_DELAY = 0.3   # seconds between description API calls
COMPANY_DELAY = 1.0       # seconds between companies


def scrape_company(db, company: dict, scraper, fetch_descriptions: bool) -> dict:
    """
    Scrape one company and save jobs to DB. Platform-agnostic — works with
    any scraper that implements scrape_jobs() and get_job_details().
    Returns a result dict summarising the run.
    """
    name = company['name']
    company_id = company['id']

    start = time.time()
    log(f"Fetching {name} ({scraper.board_token})...")

    try:
        jobs = scraper.scrape_jobs(location_filter=LOCATION_FILTER)
    except Exception as e:
        duration = time.time() - start
        db.log_scrape(company_id, 'failed', error=str(e), duration=duration)
        return {'company': name, 'status': 'failed', 'error': str(e)}

    log(f"  {len(jobs)} HK jobs found")

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
            log(f"  dup  {job['title'][:55]}")
            continue

        # New job — save description (inline if available, else fetch separately)
        new_count += 1
        log(f"  NEW  {job['title'][:55]}")
        if job.get('description'):
            db.update_job_description(job_id, job['description'])
        elif fetch_descriptions:
            platform_id = job.get('greenhouse_id') or job.get('lever_id') or job.get('workday_path') or job.get('jpmorgan_id')
            if platform_id:
                try:
                    details = scraper.get_job_details(platform_id)
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
    log("=" * 55)
    log("HK Job Aggregator — Scraper (Greenhouse + Lever)")
    log(f"Mode: {'full (with descriptions)' if fetch_descriptions else 'metadata only'}")
    log("=" * 55)

    results = []

    with get_db() as db:
        all_companies = db.get_active_companies()
        company_by_name = {c['name']: c for c in all_companies}

        # ── Greenhouse companies ──────────────────────────────────
        greenhouse_companies = [
            company_by_name[name]
            for name in GREENHOUSE_TOKENS
            if name in company_by_name
        ]
        missing_gh = [name for name in GREENHOUSE_TOKENS if name not in company_by_name]
        if missing_gh:
            warn(f"Greenhouse — not in DB (run seed): {missing_gh}")

        # ── Lever companies ───────────────────────────────────────
        lever_companies = [
            company_by_name[name]
            for name in LEVER_TOKENS
            if name in company_by_name
        ]
        missing_lv = [name for name in LEVER_TOKENS if name not in company_by_name]
        if missing_lv:
            warn(f"Lever — not in DB (run seed): {missing_lv}")

        # ── Workday companies ─────────────────────────────────────
        workday_companies = [
            company_by_name[name]
            for name in WORKDAY_TOKENS
            if name in company_by_name
        ]
        missing_wd = [name for name in WORKDAY_TOKENS if name not in company_by_name]
        if missing_wd:
            warn(f"Workday — not in DB (run seed): {missing_wd}")

        # ── Goldman Sachs (custom GraphQL) ────────────────────────
        goldman_companies = [
            company_by_name[name]
            for name in GOLDMAN_COMPANIES
            if name in company_by_name
        ]
        missing_gs = [name for name in GOLDMAN_COMPANIES if name not in company_by_name]
        if missing_gs:
            warn(f"Goldman — not in DB (run seed): {missing_gs}")

        # ── JPMorgan (Oracle HCM) ─────────────────────────────────
        jpmorgan_companies = [
            company_by_name[name]
            for name in JPMORGAN_COMPANIES
            if name in company_by_name
        ]
        missing_jpm = [name for name in JPMORGAN_COMPANIES if name not in company_by_name]
        if missing_jpm:
            warn(f"JPMorgan — not in DB (run seed): {missing_jpm}")

        total = (len(greenhouse_companies) + len(lever_companies) + len(workday_companies)
                 + len(goldman_companies) + len(jpmorgan_companies))
        log(f"{total} companies to scrape ({len(greenhouse_companies)} Greenhouse, {len(lever_companies)} Lever, "
            f"{len(workday_companies)} Workday, {len(goldman_companies)} Goldman, {len(jpmorgan_companies)} JPMorgan)\n")

        for company in greenhouse_companies:
            group(company['name'])
            scraper = GreenhouseScraper(company['name'], GREENHOUSE_TOKENS[company['name']])
            result = scrape_company(db, company, scraper, fetch_descriptions)
            results.append(result)

            if result['status'] == 'skipped':
                warn(f"Skipped: {result['reason']}")
            elif result['status'] == 'failed':
                error(f"Failed: {result.get('error', 'unknown')}")
            else:
                log(
                    f"Done — {result['new']} new, "
                    f"{result['duplicates']} dupes, "
                    f"{result['found']} HK jobs ({result.get('duration', 0)}s)"
                )
            endgroup()
            time.sleep(COMPANY_DELAY)

        # ── Lever companies ───────────────────────────────────────
        for company in lever_companies:
            group(company['name'])
            scraper = LeverScraper(company['name'], LEVER_TOKENS[company['name']])
            result = scrape_company(db, company, scraper, fetch_descriptions)
            results.append(result)

            if result['status'] == 'skipped':
                warn(f"Skipped: {result['reason']}")
            elif result['status'] == 'failed':
                error(f"Failed: {result.get('error', 'unknown')}")
            else:
                log(
                    f"Done — {result['new']} new, "
                    f"{result['duplicates']} dupes, "
                    f"{result['found']} HK jobs ({result.get('duration', 0)}s)"
                )
            endgroup()
            time.sleep(COMPANY_DELAY)

        # ── Workday companies ─────────────────────────────────────
        for company in workday_companies:
            group(company['name'])
            cfg = WORKDAY_TOKENS[company['name']]
            scraper = WorkdayScraper(company['name'], cfg['tenant'], cfg['wd'], cfg['site'])
            result = scrape_company(db, company, scraper, fetch_descriptions)
            results.append(result)

            if result['status'] == 'skipped':
                warn(f"Skipped: {result['reason']}")
            elif result['status'] == 'failed':
                error(f"Failed: {result.get('error', 'unknown')}")
            else:
                log(
                    f"Done — {result['new']} new, "
                    f"{result['duplicates']} dupes, "
                    f"{result['found']} HK jobs ({result.get('duration', 0)}s)"
                )
            endgroup()
            time.sleep(COMPANY_DELAY)

        # ── JPMorgan (Oracle HCM) ─────────────────────────────────
        for company in jpmorgan_companies:
            group(company['name'])
            scraper = JPMorganScraper(company['name'])
            result = scrape_company(db, company, scraper, fetch_descriptions)
            results.append(result)

            if result['status'] == 'skipped':
                warn(f"Skipped: {result['reason']}")
            elif result['status'] == 'failed':
                error(f"Failed: {result.get('error', 'unknown')}")
            else:
                log(
                    f"Done — {result['new']} new, "
                    f"{result['duplicates']} dupes, "
                    f"{result['found']} HK jobs ({result.get('duration', 0)}s)"
                )
            endgroup()
            time.sleep(COMPANY_DELAY)

        # ── Goldman Sachs (custom GraphQL) ────────────────────────
        for company in goldman_companies:
            group(company['name'])
            scraper = GoldmanScraper(company['name'])
            result = scrape_company(db, company, scraper, fetch_descriptions)
            results.append(result)

            if result['status'] == 'skipped':
                warn(f"Skipped: {result['reason']}")
            elif result['status'] == 'failed':
                error(f"Failed: {result.get('error', 'unknown')}")
            else:
                log(
                    f"Done — {result['new']} new, "
                    f"{result['duplicates']} dupes, "
                    f"{result['found']} HK jobs ({result.get('duration', 0)}s)"
                )
            endgroup()
            time.sleep(COMPANY_DELAY)

        # ── Summary ──────────────────────────────────────────────
        total_new   = sum(r.get('new', 0) for r in results if r['status'] == 'success')
        total_found = sum(r.get('found', 0) for r in results if r['status'] == 'success')
        failed  = [r for r in results if r['status'] == 'failed']
        skipped = [r for r in results if r['status'] == 'skipped']

        group("Scrape Summary")
        col = 35
        log(f"{'Company':<{col}} {'HK Found':>9} {'New':>6} {'Dupes':>6}  Status")
        log("-" * (col + 30))
        for r in results:
            if r['status'] == 'success':
                log(f"{r['company']:<{col}} {r['found']:>9} {r['new']:>6} {r['duplicates']:>6}  ✓")
            elif r['status'] == 'skipped':
                log(f"{r['company']:<{col}} {'—':>9} {'—':>6} {'—':>6}  ⊘ skipped")
            else:
                log(f"{r['company']:<{col}} {'—':>9} {'—':>6} {'—':>6}  ✗ FAILED")
        log("-" * (col + 30))
        log(f"{'TOTAL':<{col}} {total_found:>9} {total_new:>6}")

        if failed:
            warn(f"Failures: {[r['company'] for r in failed]}")

        stats = db.get_stats()
        log(f"\nDB: {stats['new_jobs']} unscored jobs | {stats['total_companies']} active companies")
        endgroup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape all Greenhouse companies")
    parser.add_argument(
        '--no-descriptions',
        action='store_true',
        help='Skip fetching full job descriptions (faster, but needed for AI matching)',
    )
    args = parser.parse_args()

    scrape_all(fetch_descriptions=not args.no_descriptions)
