# HK Job Aggregator

Automated job monitoring for Hong Kong finance roles. Scrapes job postings from target companies, uses AI to match against your CV, and sends a daily email digest of the best fits.

## How It Works

```
GitHub Actions (daily, 8am HKT)
  → Scrape Greenhouse ATS companies
    → Store & deduplicate in Supabase (PostgreSQL)
      → AI match new jobs against CV (GPT-4o-mini / Claude Haiku)
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
│   ├── db.py                 # Database interface
│   └── schema.sql            # Database schema
├── scrapers/
│   ├── base_scraper.py       # Abstract base scraper
│   ├── greenhouse_scraper.py # Greenhouse ATS scraper
│   └── citadel_scraper.py    # Citadel custom scraper (WIP)
├── data/                     # Local SQLite data (gitignored)
├── scrape_and_save.py        # Main scraping entry point
├── seed_companies.py         # Seed 15 target companies
├── test_db.py                # Database test suite
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variables template
```

## Quick Start

```bash
cd hk-job-aggregator
pip install -r requirements.txt
cp .env.example .env          # Edit with your credentials

python seed_companies.py      # Seed target companies
python scrape_and_save.py     # Scrape jobs from Jump Trading
python test_db.py             # Run database tests
```

## Current Status

- **Phase 1**: Database migration (SQLite → Supabase) — not started
- **Phase 2**: Expand Greenhouse scrapers — in progress
- **Phase 3**: AI job matching — not started
- **Phase 4**: Email notifications — not started
- **Phase 5**: GitHub Actions scheduler — not started

See **[PLAN.md](./PLAN.md)** for the full implementation roadmap.

## Tech Stack

- **Scraping**: Python, Requests, BeautifulSoup, Greenhouse API
- **Database**: Supabase (PostgreSQL) — migrating from SQLite
- **AI Matching**: GPT-4o-mini or Claude Haiku
- **Email**: Gmail SMTP
- **Scheduler**: GitHub Actions (cron)

## Cost

~$1-2/month (AI API calls only). Everything else is free tier.
