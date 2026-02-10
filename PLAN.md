# HK Job Aggregator — Implementation Plan

## Overview
Automated pipeline: Scrape jobs → Store in DB → AI match against CV → Email daily digest

## Phase 1: Database Migration (SQLite → Supabase PostgreSQL)
- [ ] Create Supabase project (free tier)
- [ ] Adapt schema.sql for PostgreSQL syntax (e.g., AUTOINCREMENT → SERIAL, datetime handling)
- [ ] Replace `models/db.py` SQLite calls with psycopg2 or Supabase Python client
- [ ] Migrate existing company seeds and job data
- [ ] Update `.env` with Supabase connection string
- [ ] Verify all tests pass against new DB

## Phase 2: Expand Greenhouse Scrapers
- [ ] Generalize `greenhouse_scraper.py` to accept any Greenhouse board token
- [ ] Research and add more Greenhouse-based companies (beyond Jump, DRW, Citadel)
- [ ] Fetch full job descriptions from Greenhouse API (currently only metadata)
- [ ] Create `scrape_all.py` — loop through all Greenhouse companies and scrape
- [ ] Add HK location filtering (only jobs in Hong Kong / APAC)
- [ ] Handle rate limiting and error recovery

## Phase 3: AI Job Matching
- [ ] Choose API: OpenAI GPT-4o-mini (~$0.15/1M input tokens) or Claude Haiku
- [ ] Sign up for API, set up billing
- [ ] Store CV text in `profile` table
- [ ] Create `matcher.py`:
  - Send job description + CV to AI
  - Prompt: "Score this job 0-1 for fit, give reasons"
  - Parse response → update `match_score` and `match_reasons` in jobs table
- [ ] Run matcher on new jobs only (avoid re-scoring)
- [ ] Set match threshold (default 0.6, configurable)

## Phase 4: Email Notifications (Gmail SMTP)
- [ ] Set up Gmail App Password (2FA required)
- [ ] Create `emailer.py`:
  - Query `jobs_to_notify` view
  - Build HTML email template (job title, company, score, reasons, link)
  - Send via `smtplib` with TLS
  - Mark jobs as notified after sending
- [ ] Handle empty days (no email if no new matches)
- [ ] Add unsubscribe/config options (optional)

## Phase 5: GitHub Actions Scheduler
- [ ] Create `.github/workflows/daily-scrape.yml`
- [ ] Cron schedule: `0 0 * * *` (midnight UTC = 8am HKT)
- [ ] Workflow steps:
  1. Checkout repo
  2. Set up Python + install deps
  3. Run `scrape_all.py` (scrape all companies)
  4. Run `matcher.py` (AI score new jobs)
  5. Run `emailer.py` (send daily digest)
- [ ] Store secrets in GitHub Secrets:
  - `SUPABASE_URL`, `SUPABASE_KEY`
  - `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
  - `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`
  - `NOTIFY_EMAIL` (recipient)
- [ ] Add error handling and failure notifications

## Phase 6: Future Expansion
- [ ] Add Workday scraper (Goldman, HSBC, JPMorgan, BofA)
- [ ] Add custom page scrapers (Jane Street, Barclays, Flow Traders, etc.)
- [ ] Add web dashboard (FastAPI + simple frontend)
- [ ] Add job application tracking (applied/interview/offer statuses)
- [ ] Add multiple notification channels (Slack, Telegram)

## Cost Estimate (Monthly)
- Supabase: Free tier (500MB, 50K rows)
- GitHub Actions: Free for public repos (2000 min/month)
- AI API: ~$0.50-2.00/month (estimating ~100 jobs/day, ~1K tokens each)
- Gmail SMTP: Free
- **Total: ~$1-2/month**

## Priority Order
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
(Each phase builds on the previous one)
