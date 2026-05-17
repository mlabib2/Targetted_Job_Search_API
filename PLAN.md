# HK Job Aggregator — Status

_Last updated: 2026-05-17_

All core features are built and running. This file tracks what's done and what remains.
Active task list is in `hk-job-aggregator/TODO.md`.

---

## What's built

| Feature | Status | Notes |
|---|---|---|
| Supabase PostgreSQL DB | ✓ Done | `models/db.py`, psycopg2, dedup via job_hash |
| Greenhouse scraper | ✓ Done | 16 companies, HK location filter, full descriptions |
| Workday scraper | ✓ Done | 9 companies, tenant + site config per company |
| Goldman Sachs scraper | ✓ Done | Custom GraphQL API — full descriptions |
| JPMorgan scraper | ✓ Done | Oracle HCM REST — ~131 HK jobs |
| Standard Chartered scraper | ✓ Done | J2W sitemap — ~112 HK jobs (titles only) |
| Lever scraper | ✓ Built | Code ready; no active companies use Lever |
| AI scoring | ✓ Done | `matcher.py`, Claude Haiku, batch of 5 jobs/call |
| Email digest | ✓ Done | `emailer.py`, HTML, scored jobs + unscored fallback |
| GitHub Actions cron | ✓ Done | Daily at 5am HKT, failure email on pipeline error |
| Application tracking | ✓ Done | `track.py` CLI — list / set / stats |
| PostgreSQL schema file | ✓ Done | `models/schema.sql` — up to date |

## What's pending

| Feature | Effort | Notes |
|---|---|---|
| PIMCO + Coatue Workday URLs | 5 min each | Need to find site name by visiting careers page in browser |
| Citadel hedge fund | — | Confirmed dead end — Greenhouse 404, Lever 404, careers page 403 |
| Slack / Telegram notifications | 1–2 hrs | Alternative to email |

See `hk-job-aggregator/TODO.md` for full company coverage details.

---

## Architecture

```
GitHub Actions cron (5am HKT daily)
  └─ scrape_all.py
       ├─ GreenhouseScraper     × 16 companies
       ├─ WorkdayScraper        × 9 companies
       ├─ GoldmanScraper        × 1 company (GraphQL)
       ├─ JPMorganScraper       × 1 company (Oracle HCM)
       └─ StandardCharteredScraper × 1 company (J2W sitemap)
            │
            ▼ new jobs stored in Supabase (dedup by job_hash + url)
  └─ matcher.py
       └─ Claude Haiku — batch 5 jobs/call — scores 0.0–1.0
            │
            ▼ match_score + match_reasons written to DB
  └─ emailer.py
       └─ HTML digest — scored jobs (sorted by score) + unscored fallback
            │
            ▼ notified_at set — no duplicate emails

Local tools (not in CI):
  └─ track.py  — application status CLI (applied / interviewing / offer / rejected)
```

## Monthly cost

| Service | Cost |
|---|---|
| Supabase | Free (500 MB, 50 K rows) |
| GitHub Actions | Free (public repo) |
| Claude Haiku | ~$0.50–2.00 |
| Gmail SMTP | Free |
| **Total** | **~$1–2/month** |

## GitHub Secrets required

| Secret | Purpose |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Claude Haiku for AI scoring |
| `GMAIL_ADDRESS` | Sender Gmail account |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not account password) |
| `NOTIFY_EMAIL` | Recipient(s), comma-separated |
