# HK Job Aggregator

Automated job monitoring for Hong Kong finance and quant roles. Scrapes job postings from 28 target companies across 5 ATS platforms, uses AI to match against your CV, and sends a daily email digest of the best fits.

## Pipeline

```
GitHub Actions (daily, 5am HKT)
  → Scrape 28 companies across 5 ATS platforms
    → Store & deduplicate in Supabase (PostgreSQL)
      → AI-score new jobs against CV (Claude Haiku)
        → Email daily digest via Gmail SMTP
```

## Companies Scraped (28 active)

### Greenhouse (16 companies)
| Company | Token | Typical HK Jobs |
|---|---|---|
| Qube Research & Technologies | `quberesearchandtechnologies` | ~24 |
| Jane Street | `janestreet` | ~17 |
| Point72 | `point72` | ~9 |
| Squarepoint Capital | `squarepointcapital` | ~9 |
| Tower Research Capital | `towerresearchcapital` | ~7 |
| Flow Traders | `flowtraders` | ~6 |
| Schonfeld | `schonfeld` | ~6 |
| Jump Trading | `jumptrading` | ~4 |
| Optiver | `optiverus` | ~3 |
| IMC Trading | `imc` | ~2 |
| Man Group | `mangroup` | ~2 |
| Virtu Financial | `virtu` | ~2 |
| Engineers Gate | `engineersgate` | ~2 |
| WorldQuant | `worldquant` | ~1 |
| DRW | `drweng` | ~1 |
| Hudson River Trading | `wehrtyou` | ~1 |

### Workday (9 companies)
| Company | Tenant / Site |
|---|---|
| Morgan Stanley | `ms.wd5 / External` |
| Barclays | `barclays.wd3 / External_Career_Site_Barclays` |
| Deutsche Bank | `db.wd3 / DBWebsite` |
| Macquarie | `mq.wd3 / CareersatMQ` |
| BlackRock | `blackrock.wd1 / BlackRock_Professional` |
| HKEX | `hkex.wd3 / HKEXCareerPage` |
| Fidelity International | `fil.wd3 / 001` |
| State Street | `statestreet.wd1 / Global` |
| Brevan Howard | `brevanhoward.wd3 / BH_ExternalCareers` |

### Custom scrapers (3 companies)
| Company | Method | Notes |
|---|---|---|
| Goldman Sachs | Custom GraphQL API | `api-higher.gs.com` — full descriptions |
| JPMorgan Chase | Oracle HCM REST API | `jpmc.fa.oraclecloud.com` — ~131 HK jobs |
| Standard Chartered | J2W sitemap | ~112 HK jobs — titles only (JS-rendered site) |

## Project Structure

```
hk-job-aggregator/
├── scrapers/
│   ├── greenhouse_scraper.py          # Greenhouse ATS (16 companies)
│   ├── workday_scraper.py             # Workday (9 companies)
│   ├── goldman_scraper.py             # Goldman Sachs — custom GraphQL
│   ├── jpmorgan_scraper.py            # JPMorgan — Oracle HCM REST
│   ├── standard_chartered_scraper.py  # Standard Chartered — J2W sitemap
│   └── lever_scraper.py               # Lever (built, no active tokens)
├── models/
│   ├── db.py                          # Supabase (PostgreSQL) interface
│   └── schema.sql                     # PostgreSQL schema
├── scrape_all.py                      # Main scrape entry point
├── matcher.py                         # AI scoring (Claude Haiku)
├── emailer.py                         # HTML digest + Gmail SMTP
├── track.py                           # Application status CLI
├── seed_companies.py                  # Seed/update company list in DB
├── test_scrapers.py                   # Health check — run before dev sessions
├── test_db.py                         # DB connection + operations test
├── utils.py                           # Shared helpers (strip_html, etc.)
└── data/cv.txt                        # Your CV — used for AI matching
```

## Quick Start

```bash
cd hk-job-aggregator
pip install -r requirements.txt
# create a .env file with DATABASE_URL, ANTHROPIC_API_KEY, GMAIL_ADDRESS,
# GMAIL_APP_PASSWORD, NOTIFY_EMAIL

python seed_companies.py        # register companies in Supabase
python test_scrapers.py --fast  # sanity check before scraping

python scrape_all.py            # scrape all 28 companies
python matcher.py               # AI-score new jobs against CV
python emailer.py --dry-run     # preview digest (saves digest_preview.html)
python emailer.py               # send digest email
```

## Application Tracking

`track.py` is a local CLI for tracking which jobs you've applied to.

```bash
python track.py list                        # new jobs scoring >= 0.6
python track.py list --status applied       # list by status
python track.py list --status new --all     # all new jobs regardless of score
python track.py set <job_id> applied        # mark as applied
python track.py set <job_id> interviewing   # in interviews
python track.py set <job_id> offer          # received an offer
python track.py set <job_id> rejected       # rejected / pass
python track.py stats                       # pipeline overview
```

Valid statuses: `new` → `seen` → `applied` → `interviewing` → `offer` / `rejected`

## Health Check

Run this at the start of any dev session to catch broken endpoints before committing to a full scrape:

```bash
python test_scrapers.py           # ~3 min — DB + 1 company per platform
python test_scrapers.py --fast    # ~20s  — DB + 3 Greenhouse only
python test_scrapers.py --full    # ~10 min — every company, every platform
```

## GitHub Actions

Runs daily at 5am HKT (`0 21 * * *` UTC). Secrets required:

| Secret | Description |
|---|---|
| `DATABASE_URL` | Supabase connection string (`postgresql://...`) |
| `ANTHROPIC_API_KEY` | Claude API key for AI scoring |
| `GMAIL_ADDRESS` | Gmail address to send from |
| `GMAIL_APP_PASSWORD` | Gmail app password |
| `NOTIFY_EMAIL` | Recipient(s) — comma-separated for multiple |

## Tech Stack

| Layer | Tech |
|---|---|
| Scraping | Python + Requests, 5 ATS platforms |
| Database | Supabase (PostgreSQL) via psycopg2 |
| AI Matching | Claude Haiku (`claude-haiku-4-5-20251001`) |
| Email | Gmail SMTP, HTML digest |
| Scheduler | GitHub Actions cron |

## Cost

~$1–3/month (Claude API calls only). GitHub Actions, Supabase, and Gmail are all free tier.
