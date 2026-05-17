"""
test_scrapers.py — Health check for all scrapers and the DB connection.

Run this at the start of any dev session to catch broken endpoints before
committing to a full scrape run.

Usage:
    python test_scrapers.py            # test one company per platform (~2–3 min)
    python test_scrapers.py --fast     # DB + Greenhouse only (~20 s)
    python test_scrapers.py --full     # every company in every platform (~10 min)

Exit code: 0 if all tests pass, 1 if any fail.
"""

import time
import sys
import argparse
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, ".")

# ── Config ────────────────────────────────────────────────────────────────────

LOCATION_FILTER = "Hong Kong"

# HK location strings that count as a valid HK job location
HK_LOCATION_HINTS = [
    "Hong Kong", "Central", "Kwun Tong", "Quarry Bay",
    "Admiralty", "Wan Chai", "Sheung Wan",
]

REQUIRED_FIELDS = {"title", "url", "location", "company"}

# One representative company per Greenhouse board (not all 16 — that's slow)
GREENHOUSE_SPOT_CHECKS = {
    "Qube Research & Technologies": "quberesearchandtechnologies",  # most HK jobs
    "Jane Street":                  "janestreet",
    "Jump Trading":                 "jumptrading",
}

# One representative company per Workday board.
# 'location_filter' overrides the default "Hong Kong" for companies with non-standard location strings.
WORKDAY_SPOT_CHECKS = {
    # HKEX uses internal codes ("HK-TWO ES 10/F") not "Hong Kong"
    "HKEX":          {"tenant": "hkex",  "wd": "wd3", "site": "HKEXCareerPage", "location_filter": "HK-"},
    "Morgan Stanley Hong Kong": {"tenant": "ms", "wd": "wd5", "site": "External"},
}

# ── Helpers ───────────────────────────────────────────────────────────────────

class Result:
    def __init__(self, name: str):
        self.name = name
        self.passed: Optional[bool] = None
        self.message: str = ""
        self.job_count: int = 0
        self.hk_count: int = 0
        self.duration: float = 0.0

    def ok(self, msg: str, jobs: List[dict]):
        self.passed = True
        self.job_count = len(jobs)
        self.hk_count = _hk_count(jobs)
        self.message = msg

    def fail(self, msg: str):
        self.passed = False
        self.message = msg

    def skip(self, msg: str):
        self.passed = None
        self.message = msg


def _hk_count(jobs: List[dict]) -> int:
    count = 0
    for j in jobs:
        loc = j.get("location") or ""
        if any(hint in loc for hint in HK_LOCATION_HINTS):
            count += 1
    return count


def _validate(jobs: List[dict]) -> Tuple[bool, str]:
    """Check job list is non-empty and well-structured."""
    if not jobs:
        return False, "0 jobs returned"
    bad = []
    for i, job in enumerate(jobs[:5]):
        missing = [f for f in REQUIRED_FIELDS if not job.get(f)]
        if missing:
            bad.append(f"job[{i}] missing {missing}")
    if bad:
        return False, "; ".join(bad[:3])
    return True, f"{len(jobs)} jobs"


def _run(result: Result, fn):
    """Run fn(), catching exceptions. Populates result.duration."""
    t0 = time.time()
    try:
        fn(result)
    except Exception as e:
        result.fail(str(e)[:120])
    result.duration = round(time.time() - t0, 1)


# ── Individual tests ──────────────────────────────────────────────────────────

def test_db(result: Result):
    from models.db import get_db
    with get_db() as db:
        stats = db.get_stats()
        companies = db.get_active_companies()
        result.ok(
            f"{len(companies)} companies | {stats['new_jobs']} unscored jobs",
            []
        )
        result.job_count = stats["new_jobs"]


def test_greenhouse(name: str, token: str, result: Result):
    from scrapers.greenhouse_scraper import GreenhouseScraper
    scraper = GreenhouseScraper(name, token)
    jobs = scraper.scrape_jobs(location_filter=LOCATION_FILTER)
    ok, msg = _validate(jobs)
    if ok:
        result.ok(msg, jobs)
    else:
        result.fail(msg)


def test_workday(name: str, cfg: dict, result: Result):
    from scrapers.workday_scraper import WorkdayScraper
    scraper = WorkdayScraper(name, cfg["tenant"], cfg["wd"], cfg["site"])
    loc = cfg.get("location_filter", LOCATION_FILTER)
    jobs = scraper.scrape_jobs(location_filter=loc)
    ok, msg = _validate(jobs)
    if ok:
        result.ok(msg, jobs)
    else:
        result.fail(msg)


def test_goldman(result: Result):
    from scrapers.goldman_scraper import GoldmanScraper
    scraper = GoldmanScraper("Goldman Sachs Hong Kong")
    jobs = scraper.scrape_jobs(location_filter=LOCATION_FILTER)
    ok, msg = _validate(jobs)
    if ok:
        result.ok(msg, jobs)
    else:
        result.fail(msg)


def test_jpmorgan(result: Result):
    from scrapers.jpmorgan_scraper import JPMorganScraper
    scraper = JPMorganScraper("JPMorgan Chase Hong Kong")
    jobs = scraper.scrape_jobs(location_filter=LOCATION_FILTER)
    ok, msg = _validate(jobs)
    if ok:
        hk = _hk_count(jobs)
        if hk == 0:
            result.fail(f"HK filter not working — {len(jobs)} jobs but 0 in HK")
        else:
            result.ok(msg, jobs)
    else:
        result.fail(msg)


def test_standard_chartered(result: Result):
    from scrapers.standard_chartered_scraper import StandardCharteredScraper
    scraper = StandardCharteredScraper("Standard Chartered Hong Kong")
    jobs = scraper.scrape_jobs(location_filter=LOCATION_FILTER)
    ok, msg = _validate(jobs)
    if ok:
        result.ok(msg, jobs)
    else:
        result.fail(msg)


# ── Full-platform sweep (--full mode) ─────────────────────────────────────────

GREENHOUSE_ALL = {
    "Qube Research & Technologies": "quberesearchandtechnologies",
    "Jane Street":                  "janestreet",
    "Point72":                      "point72",
    "Squarepoint Capital":          "squarepointcapital",
    "Tower Research Capital":       "towerresearchcapital",
    "Flow Traders":                 "flowtraders",
    "Schonfeld":                    "schonfeld",
    "Jump Trading":                 "jumptrading",
    "IMC Trading":                  "imc",
    "Man Group":                    "mangroup",
    "WorldQuant":                   "worldquant",
    "DRW":                          "drweng",
    "Hudson River Trading":         "wehrtyou",
    "Optiver":                      "optiverus",
    "Virtu Financial":              "virtu",
    "Engineers Gate":               "engineersgate",
}

WORKDAY_ALL = {
    "Morgan Stanley Hong Kong": {"tenant": "ms",         "wd": "wd5", "site": "External"},
    "Barclays Hong Kong":       {"tenant": "barclays",   "wd": "wd3", "site": "External_Career_Site_Barclays"},
    "Deutsche Bank":            {"tenant": "db",         "wd": "wd3", "site": "DBWebsite"},
    "Macquarie":                {"tenant": "mq",         "wd": "wd3", "site": "CareersatMQ"},
    "BlackRock":                {"tenant": "blackrock",  "wd": "wd1", "site": "BlackRock_Professional"},
    "HKEX":                     {"tenant": "hkex",       "wd": "wd3", "site": "HKEXCareerPage", "location_filter": "HK-"},
    "Fidelity International":   {"tenant": "fil",        "wd": "wd3", "site": "001"},
    "State Street":             {"tenant": "statestreet","wd": "wd1", "site": "Global"},
    "Brevan Howard":            {"tenant": "brevanhoward", "wd": "wd3", "site": "BH_ExternalCareers"},
}


# ── Runner ────────────────────────────────────────────────────────────────────

def run_suite(fast: bool = False, full: bool = False) -> List[Result]:
    results: List[Result] = []

    # ── DB ──────────────────────────────────────────────────────────────────
    print("\n── Database connection")
    r = Result("Database (Supabase)")
    _run(r, test_db)
    results.append(r)
    _print_result(r)

    # ── Greenhouse ──────────────────────────────────────────────────────────
    gh_targets = GREENHOUSE_ALL if full else GREENHOUSE_SPOT_CHECKS
    print(f"\n── Greenhouse ({len(gh_targets)} {'all' if full else 'spot-check'})")
    for name, token in gh_targets.items():
        r = Result(f"Greenhouse · {name}")
        _run(r, lambda res, n=name, t=token: test_greenhouse(n, t, res))
        results.append(r)
        _print_result(r)

    if fast:
        _print_summary(results)
        return results

    # ── Workday ─────────────────────────────────────────────────────────────
    wd_targets = WORKDAY_ALL if full else WORKDAY_SPOT_CHECKS
    print(f"\n── Workday ({len(wd_targets)} {'all' if full else 'spot-check'})")
    for name, cfg in wd_targets.items():
        r = Result(f"Workday · {name}")
        _run(r, lambda res, n=name, c=cfg: test_workday(n, c, res))
        results.append(r)
        _print_result(r)

    # ── Goldman Sachs (GraphQL) ─────────────────────────────────────────────
    print("\n── Custom scrapers")
    r = Result("Goldman Sachs (GraphQL)")
    _run(r, test_goldman)
    results.append(r)
    _print_result(r)

    # ── JPMorgan (Oracle HCM) ───────────────────────────────────────────────
    r = Result("JPMorgan (Oracle HCM)")
    _run(r, test_jpmorgan)
    results.append(r)
    _print_result(r)

    # ── Standard Chartered (J2W sitemap) ────────────────────────────────────
    r = Result("Standard Chartered (J2W sitemap)")
    _run(r, test_standard_chartered)
    results.append(r)
    _print_result(r)

    return results


# ── Output ────────────────────────────────────────────────────────────────────

def _print_result(r: Result):
    icon = "✓" if r.passed else ("⊘" if r.passed is None else "✗")
    hk_str = f"  {r.hk_count} HK" if r.hk_count else ""
    print(f"  {icon}  {r.name:<45} {r.message}{hk_str}  ({r.duration}s)")


def _print_summary(results: List[Result]):
    passed  = [r for r in results if r.passed is True]
    failed  = [r for r in results if r.passed is False]
    skipped = [r for r in results if r.passed is None]

    print()
    print("=" * 60)
    print(f"  Results: {len(passed)} passed  {len(failed)} failed  {len(skipped)} skipped")
    print("=" * 60)

    if failed:
        print("\nFailed:")
        for r in failed:
            print(f"  ✗  {r.name}")
            print(f"       {r.message}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Health check for all scrapers")
    parser.add_argument(
        "--fast", action="store_true",
        help="DB + Greenhouse spot-check only (~20s)"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Test every company in every platform (~10 min)"
    )
    args = parser.parse_args()

    print("HK Job Aggregator — Scraper Health Check")
    print(f"Mode: {'fast' if args.fast else 'full' if args.full else 'default'}")

    results = run_suite(fast=args.fast, full=args.full)
    _print_summary(results)

    failed = [r for r in results if r.passed is False]
    sys.exit(1 if failed else 0)
