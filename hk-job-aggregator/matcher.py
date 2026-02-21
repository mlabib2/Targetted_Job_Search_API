"""
matcher.py — Score unscored jobs against CV using Claude Haiku

Batches 5 jobs per API call (~80% fewer calls vs 1-by-1).
Pre-filters obvious mismatches by title (zero API cost).
Only processes jobs with match_score IS NULL.

DB safety rules:
  - A job is only saved if its result is fully valid (score + reasons parsed)
  - If a job is missing from the API response, it stays NULL → retried next run
  - If a batch fails entirely, falls back to 1-by-1 scoring for those jobs
  - Score 0.5 is never assumed as a default — ambiguity = retry

Usage:
    python matcher.py              # score all unscored jobs
    python matcher.py --dry-run   # print scores without saving to DB
"""

import sys
import os
import re
import json
import time
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import anthropic
from dotenv import load_dotenv
from models.db import get_db

load_dotenv()

CV_PATH = Path(__file__).parent / "data" / "cv.txt"
MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 5
RATE_LIMIT_DELAY = 0.5
MATCH_THRESHOLD = 0.6

FILTER_FUNCTIONS = [
    r"\bpayroll\b", r"\bprocurement\b", r"\brecruiter\b", r"\brecruiting\b",
    r"\btalent acquisition\b", r"\bhuman resources\b",
    r"\boffice manager\b", r"\bexecutive assistant\b", r"\badministrative\b",
    r"\baccountant\b", r"\baudit\b", r"\blegal counsel\b",
    r"\bmarketing\b", r"\bsales\b",
    r"\bgraphic design\b", r"\bcontent writer\b", r"\bcopywriter\b",
    r"\binterior design\b", r"\bfacilities\b",
]

BATCH_SYSTEM_PROMPT = """You are evaluating job fit for a specific candidate targeting HK hedge fund and quant trading roles.

CANDIDATE PROFILE:
- Fresh graduate: BSc Computer Science + Minor Finance & Economics, City University of Hong Kong, First Class Honors (graduating May 2026)
- Current role: Software Engineer / Trade Desk Ops (contractor) at a HK hedge fund — trading infrastructure, market data pipelines (Bloomberg, Refinitiv), FastAPI services, PostgreSQL, AWS Lambda/EC2, CI/CD, risk/compliance layer
- Previous: Quant Developer intern (C++ fully automated options trading on IBKR, backtesting, QuantConnect), SWE intern (FastAPI/Django), PwC analytics placement (SQL, Power BI, AWS)
- Skills: C++, Python, SQL, FastAPI, PostgreSQL, Redis, Docker, AWS, Bloomberg, IBKR, QuantConnect, GitHub Actions
- CFA Level I candidate (2026); based in Hong Kong

SCORING RUBRIC (0.0–1.0) — experience level is the #1 factor:
- 0.85–1.00: Campus/graduate/new grad program, "0–1 year" experience, or entry-level at a quant/trading firm with strong stack overlap
- 0.65–0.85: Junior role (1–2 yrs acceptable), strong overlap with his trading-systems/quant/backend tech stack
- 0.45–0.65: Partial fit — relevant domain but moderate experience gap, or role needs skills he partially has
- 0.20–0.45: Too senior (3+ years required), limited stack overlap, or stretch role
- 0.00–0.20: Explicitly senior (VP, Director, MD, Head of, Principal, 5+ yrs) OR completely wrong function

BOOST score for:
- Title contains: Graduate, New Grad, Campus, Associate, Junior, Entry-Level, Analyst
- Requires 0–2 years experience
- Mentions: C++, Python, trading systems, quant/algo, options/derivatives, market data, hedge fund tech
- Located in Hong Kong

PENALISE score for:
- Title or requirements: Senior, VP, Vice President, Director, Managing Director, Head of, Principal (unless clearly entry track)
- Requires 3+ years experience
- Non-technical functions: operations management, compliance, legal, sales, finance/accounting (not quant)

You will receive a CV and a numbered list of jobs.
Respond ONLY with a valid JSON array, one object per job, in order:
[
  {"job": 1, "score": 0.88, "reasons": ["Graduate program at quant firm", "C++ and Python match", "HK based"]},
  {"job": 2, "score": 0.22, "reasons": ["Requires 5+ years experience", "Director-level role"]}
]

2–3 short, specific reasons per job. Mention what matches AND what's missing."""

SINGLE_SYSTEM_PROMPT = """You are evaluating job fit for a specific candidate.

CANDIDATE: Fresh graduate (May 2026), BSc Computer Science + Minor Finance & Economics, City University of Hong Kong, First Class Honors.
Current: HK hedge fund SWE contractor (trading infrastructure, Bloomberg, Refinitiv, FastAPI, PostgreSQL, AWS, risk/compliance systems).
Past: Quant dev intern (C++ automated options trading, IBKR, QuantConnect), SWE intern (FastAPI/Django), PwC analytics (SQL, Power BI, AWS).
Skills: C++, Python, SQL, FastAPI, PostgreSQL, Redis, Docker, AWS, Bloomberg, QuantConnect. CFA L1 candidate. Based in HK.

SCORING — experience level is the #1 factor:
- 0.85–1.00: Campus/graduate/new grad/entry-level, 0–1 yr experience, strong stack match
- 0.65–0.85: Junior role (1–2 yrs), strong overlap with trading systems or quant/backend tech
- 0.45–0.65: Partial fit — relevant domain but experience gap or secondary skills needed
- 0.20–0.45: Too senior (3+ yrs required) or limited overlap
- 0.00–0.20: VP/MD/Director/Head of, 5+ yrs required, or wrong function entirely

Respond ONLY with valid JSON:
{"score": 0.82, "reasons": ["reason 1", "reason 2"]}

2–3 short specific reasons covering fit and gaps."""


def load_cv() -> str:
    if not CV_PATH.exists():
        raise FileNotFoundError(f"CV not found at {CV_PATH}")
    return CV_PATH.read_text().strip()


def pre_filter(title: str) -> str | None:
    """Returns filter reason if job should be skipped, else None."""
    t = title.lower()
    for pattern in FILTER_FUNCTIONS:
        if re.search(pattern, t):
            return "Pre-filtered: function mismatch"
    return None


def strip_fences(raw: str) -> str:
    """Remove markdown code fences if present."""
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())
    return raw.strip()


def validate_result(item: dict) -> tuple[float, list[str]] | None:
    """
    Validate a single result object from the API.
    Returns (score, reasons) if valid, None if invalid.
    """
    try:
        score = float(item["score"])
        if not (0.0 <= score <= 1.0):
            return None
        reasons = item.get("reasons", [])
        if not isinstance(reasons, list):
            return None
        reasons = [str(r) for r in reasons if r]
        return score, reasons
    except (KeyError, TypeError, ValueError):
        return None


def score_single(client: anthropic.Anthropic, cv: str, job: dict) -> tuple[float, list[str]] | None:
    """
    Score one job individually (fallback when batch fails).
    Returns (score, reasons) or None if parsing fails.
    """
    job_text = f"Company: {job['company_name']}\nTitle: {job['title']}"
    if job.get('description'):
        desc = re.sub(r'<[^>]+>', ' ', job['description'])
        desc = re.sub(r'\s+', ' ', desc).strip()[:2000]
        job_text += f"\n\n{desc}"

    message = client.messages.create(
        model=MODEL,
        max_tokens=200,
        system=SINGLE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"CV:\n{cv}\n\n---\n\nJob:\n{job_text}"}]
    )
    raw = strip_fences(message.content[0].text)
    try:
        data = json.loads(raw)
        return validate_result(data)
    except (json.JSONDecodeError, AttributeError):
        return None


def score_batch(client: anthropic.Anthropic, cv: str, jobs: list[dict]) -> dict[int, tuple[float, list[str]]]:
    """
    Score a batch of jobs in one API call.
    Returns dict mapping job list index → (score, reasons).
    Only includes entries that passed validation — missing = retry next run.
    """
    jobs_text = "\n\n".join(
        f"Job {i + 1}: {job['company_name']} — {job['title']}"
        + (f"\n{re.sub(chr(60) + '[^>]+' + chr(62), ' ', job['description'])[:800].strip()}"
           if job.get('description') else "")
        for i, job in enumerate(jobs)
    )

    message = client.messages.create(
        model=MODEL,
        max_tokens=200 * len(jobs),
        system=BATCH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"CV:\n{cv}\n\n---\n\nJobs to score:\n{jobs_text}"}]
    )

    raw = strip_fences(message.content[0].text)
    results_list = json.loads(raw)  # raises JSONDecodeError if malformed → caller handles

    if not isinstance(results_list, list):
        raise ValueError("API did not return a JSON array")

    validated = {}
    for item in results_list:
        try:
            idx = int(item["job"]) - 1
        except (KeyError, TypeError, ValueError):
            continue
        if not (0 <= idx < len(jobs)):
            continue
        result = validate_result(item)
        if result is not None:
            validated[idx] = result

    return validated


def run_matcher(dry_run: bool = False):
    cv = load_cv()
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    print("=" * 60)
    print(f"Job Matcher — Claude Haiku (batch={BATCH_SIZE})")
    print("=" * 60 + "\n")

    with get_db() as db:
        all_jobs = db.get_new_jobs()
        print(f"Unscored jobs: {len(all_jobs)}\n")

        if not all_jobs:
            print("Nothing to score.")
            return

        api_calls = 0
        pre_filtered = 0
        scored = 0
        matches = 0
        skipped = 0   # valid API call but job missing from response
        errors = 0

        # Step 1 — pre-filter
        to_score = []
        for job in all_jobs:
            reason = pre_filter(job['title'])
            if reason:
                print(f"⊘  {job['company_name']} — {job['title'][:50]}")
                if not dry_run:
                    db.update_job_match(job['id'], 0.0, [reason])
                pre_filtered += 1
            else:
                to_score.append(job)

        total_batches = (len(to_score) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\n{len(to_score)} jobs → {total_batches} batches of {BATCH_SIZE}\n")

        # Step 2 — batch scoring
        for batch_start in range(0, len(to_score), BATCH_SIZE):
            batch = to_score[batch_start:batch_start + BATCH_SIZE]
            batch_num = batch_start // BATCH_SIZE + 1
            print(f"── Batch {batch_num}/{total_batches} ({len(batch)} jobs)")

            try:
                results = score_batch(client, cv, batch)
                api_calls += 1

                for i, job in enumerate(batch):
                    if i not in results:
                        # Job missing from response — leave NULL, retry next run
                        print(f"  ?  {job['company_name']} — {job['title'][:45]}  (missing, will retry)")
                        skipped += 1
                        continue

                    score, reasons = results[i]
                    is_match = score >= MATCH_THRESHOLD
                    print(f"  {'✓' if is_match else '✗'}  {score:.2f}  {job['company_name']} — {job['title'][:42]}")
                    if reasons:
                        print(f"       • {reasons[0]}")

                    if not dry_run:
                        db.update_job_match(job['id'], score, reasons)
                    scored += 1
                    if is_match:
                        matches += 1

            except (json.JSONDecodeError, ValueError) as e:
                # Batch parse failed — fall back to 1-by-1 for this batch
                print(f"  Batch parse failed ({e}), falling back to individual scoring...")
                api_calls += 1  # already counted the failed batch call
                for job in batch:
                    try:
                        result = score_single(client, cv, job)
                        api_calls += 1
                        if result is None:
                            print(f"  ?  {job['company_name']} — {job['title'][:45]}  (unparseable, will retry)")
                            skipped += 1
                            continue
                        score, reasons = result
                        is_match = score >= MATCH_THRESHOLD
                        print(f"  {'✓' if is_match else '✗'}  {score:.2f}  {job['company_name']} — {job['title'][:42]}  (individual)")
                        if not dry_run:
                            db.update_job_match(job['id'], score, reasons)
                        scored += 1
                        if is_match:
                            matches += 1
                        time.sleep(RATE_LIMIT_DELAY)
                    except Exception as e2:
                        print(f"  ✗  {job['company_name']} — {job['title'][:45]}  Error: {e2}")
                        errors += 1

            except Exception as e:
                print(f"  Batch error: {e}")
                errors += len(batch)

            time.sleep(RATE_LIMIT_DELAY)

        # Summary
        print(f"\n{'='*60}")
        print(f"Done {'(dry run — nothing saved)' if dry_run else ''}")
        print(f"  Pre-filtered (no API):  {pre_filtered}")
        print(f"  Scored via API:         {scored}  ({api_calls} API calls)")
        print(f"  Scored above 0.6:       {matches}")
        print(f"  Will retry next run:    {skipped}")
        print(f"  Errors:                 {errors}")

        if not dry_run:
            stats = db.get_stats()
            print(f"  Jobs above threshold:   {stats['matching_jobs']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Score jobs but don't save to DB")
    args = parser.parse_args()

    run_matcher(dry_run=args.dry_run)
