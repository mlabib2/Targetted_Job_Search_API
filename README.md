# HK Job Aggregator

Automated job monitoring for Hong Kong finance roles. Scrapes job postings from target companies, uses AI to match against your CV, and sends a daily email digest of the best fits.

## How It Works

```
GitHub Actions (daily, 5am HKT)
  → Scrape Greenhouse ATS companies
    → Store & deduplicate in Supabase (PostgreSQL)
      → AI match new jobs against CV (Claude Haiku)
        → Email daily digest via Gmail SMTP
```

## Target Companies

| Company | ATS Platform | Status |
|---------|-------------|--------|
| Jump Trading | Greenhouse | Working |
| DRW | Greenhouse | Planned |
| Citadel Securities | Greenhouse | Planned |
| Goldman Sachs | Workday | Future |
| Morgan Stanley | Taleo | Future |
| Jane Street | Custom | Future |
| + 9 more | Various | Future |

## Project Structure

```
hk-job-aggregator/
├── models/
│   └── db.py                 # Supabase (PostgreSQL) interface
├── scrapers/
│   ├── greenhouse_scraper.py # Greenhouse ATS scraper
│   └── citadel_scraper.py    # Citadel custom scraper (WIP)
├── scrape_all.py             # Main scraping entry point
├── matcher.py                # AI job scoring (Claude Haiku)
├── emailer.py                # HTML digest builder & Gmail sender
├── seed_companies.py         # Seed target companies
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variables template
```

## Quick Start

```bash
cd hk-job-aggregator
pip install -r requirements.txt
cp .env.example .env          # Edit with your credentials

python seed_companies.py      # Seed target companies
python scrape_all.py          # Scrape jobs
python matcher.py             # Score jobs against your CV
python emailer.py --dry-run   # Preview digest (saves digest_preview.html)
python emailer.py             # Send digest email
```

## Current Status

- **Scraping**: Greenhouse ATS working (Jump Trading live, more companies planned)
- **Database**: Supabase (PostgreSQL) — dedup, views, notified tracking
- **AI Matching**: Claude Haiku scoring jobs against CV
- **Email**: HTML digest via Gmail SMTP, supports multiple recipients
- **Scheduler**: GitHub Actions cron — runs daily at 5am HKT

## GitHub Actions Setup

Add these secrets to your repo (`Settings → Secrets → Actions`):

| Secret | Description |
|--------|-------------|
| `DATABASE_URL` | Supabase connection string |
| `ANTHROPIC_API_KEY` | Claude API key for AI scoring |
| `GMAIL_ADDRESS` | Gmail address to send from |
| `GMAIL_APP_PASSWORD` | Gmail app password |
| `NOTIFY_EMAIL` | Recipient(s) — comma-separated for multiple |

## Tech Stack

- **Scraping**: Python, Requests, Greenhouse API
- **Database**: Supabase (PostgreSQL)
- **AI Matching**: Claude Haiku (Anthropic)
- **Email**: Gmail SMTP
- **Scheduler**: GitHub Actions (cron)

## Cost

~$1-2/month (AI API calls only). Everything else is free tier.
