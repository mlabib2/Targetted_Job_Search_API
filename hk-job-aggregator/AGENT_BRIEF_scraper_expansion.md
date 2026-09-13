# Brief for a fresh agent: continue scraper coverage expansion

## Context
This repo (`hk-job-aggregator`) scrapes job postings from finance/quant-trading firms for Hong
Kong (primary) and London (secondary) roles, scores them against the user's CV, and emails a daily
digest. `README.md`'s "Personal Target List Coverage" section is the authoritative reconciliation
between the user's 81-firm personal target list and what's actually wired into `scrape_all.py`
(the real source of truth for what gets scraped — always verify against it directly, not just the
README, in case they've drifted).

As of 2026-09-12: 60 companies actively scraped, 49/81 target-list firms tracked, 23 confirmed dead
ends, only **9 firms genuinely unresolved**. This session added 11 new companies (GSA Capital,
Allston Trading, Wolverine Trading, Quantbox Research, Eagle Seven, Maverick Derivatives, Geneva
Trading, Epoch Capital, Chicago Trading Company, Belvedere Trading, Valkyrie Trading) and confirmed
7 more as genuine dead ends (Chimera Securities, Algorithmic Trading Group, Marquette Partners,
Domstad Traders, Genk Capital, All Options, Z.R.T.X.).

## Task 1: Resolve the last 9 unresearched firms
See README.md's "? Not tracked — never researched" table: Deep Blue Capital, Matrix Executions,
Grace Hall Trading, Market Wizards, Prime Trading, Seven Points Capital, League Trading, Barak
Capital, Liquid Capital Group.

**Important — a real trap already hit this session:** guessing Workable/Ashby tokens from these
names (`market`, `prime`, `seven`, `deep`, `grace`, `league`, `barak`, `liquid`, `matrix`) all
return HTTP 200, but every single one is a **different, unrelated company** that happens to share
the generic slug (verified by checking the actual `name` field / job titles in the response body —
e.g. the Ashby `eagle` board posts "Forward Deployed Engineer" roles for an unrelated AI startup,
not Eagle Seven). Do not trust a bare 200 status. For each of these 9:
1. Web-search the exact firm name to confirm it's a real company and find its actual careers URL.
2. If a careers page exists, check it (ideally with a real browser render, not just `curl`, since
   several of these turned out to be JS-rendered SPAs) for what ATS it actually uses — look for the
   real linked board (often a distinctly-spelled token, e.g. `eagle-seven` not `eagle`,
   `allston-trading` not `allston`).
3. If you find a real, working board, verify company identity from the response body before adding
   it anywhere, then check job locations. Add to `scrape_all.py` (matching the existing dict
   patterns — Greenhouse/Lever/Workday/Workable all have working scraper classes in `scrapers/`)
   and register the company in `seed_companies.py` (run `python3 seed_companies.py` after — it's
   idempotent, duplicates are skipped safely). Follow the established "future-proofing" precedent:
   a real, live board with 0 current HK jobs is still worth keeping (see Mako Trading, Vatic Labs
   entries in `seed_companies.py` for the exact reasoning/comment style to match).
4. If no real board is found (email-only application, LinkedIn-only, or genuinely defunct), mark it
   a confirmed dead end in README.md with the specific reason, matching the existing dead-end
   table's format.
5. After any `scrape_all.py` change, run `python3 test_scrapers.py --fast` (and ideally the default
   mode too) to confirm no regressions before considering the change done.

## Task 2: Try additional job portals
Per the user's own suggestion and `Job_Application_Bot/session_log_2026-09-12.md`'s "possible next
steps," Indeed and Glassdoor have not been tried at all as scraping sources (only LinkedIn and
eFinancialCareers have been explored, and only manually via browser for the latter — nothing
automated). Evaluate whether either has a public/semi-public job-search API (similar to how
Greenhouse/Lever/Workable expose one) that could feed into this same pipeline, or whether they're
scrape-only/heavily bot-protected. Report findings even if the answer is "not feasible" — that's
still useful signal.

## Task 3: Keep docs in sync
Whatever you change in `scrape_all.py` / `seed_companies.py`, update `README.md`'s counts and
tables to match (the header company count, the per-platform tables, and the target-list coverage
counts/tables) — this drifted noticeably out of sync before this session and cost real time to
reconcile. Keep the three numbers (tracked + dead-end + not-researched) summing to 81 always.

## What NOT to do
- Don't touch `Job_Application_Bot/` (a separate, LinkedIn-browser-automation workflow — out of
  scope for this repo).
- Don't add a company to `scrape_all.py` off an unverified token guess — identity verification via
  the actual response body is mandatory, not optional, given the false-positive rate found this
  session.
- Don't run `python3 test_scrapers.py --full` casually — it's a ~10 minute full sweep; `--fast` or
  the unflagged default mode are enough for routine verification.
