# HK Job Aggregator

Automated job monitoring for Hong Kong finance and quant roles. Scrapes job postings from 44 target companies across 8 ATS platforms, uses AI to match against your CV, and sends a daily email digest of the best fits.

_Company count last verified against `scrape_all.py` (source of truth) on 2026-07-26 — `README.md` had drifted out of date since May 2026._

## Pipeline

```
GitHub Actions (daily, 5am HKT)
  → Scrape 44 companies across 8 ATS platforms
    → Store & deduplicate in Supabase (PostgreSQL)
      → AI-score new jobs against CV (Claude Haiku)
        → Email daily digest via Gmail SMTP
```

## Companies Scraped (44 active)

### Greenhouse (23 companies)
| Company | Token | Typical HK Jobs |
|---|---|---|
| Qube Research & Technologies | `quberesearchandtechnologies` | ~24 |
| Jane Street | `janestreet` | ~17 |
| Interactive Brokers | `ibkr` | ~17 |
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
| AQR Capital Management | `aqr` | ~1 (2 London) |
| Citadel Securities | `citadelsecurities` | 0 (board active, watch) |
| XTX Markets | `xtxmarketstechnologies` | 0 (5 total — London/NY/SG) |
| Marshall Wace | `marshallwace` | 0 HK (2 London, London filter) |
| Winton | `winton` | 0 HK (8 London, London filter) |
| PDT Partners | `pdtpartners` | 0 HK (1 London, London filter) |

### Workday (13 companies)
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
| Wellington Management | `wellington.wd5 / External` (0 HK, board active) |
| Dimensional Fund Advisors | `dimensional.wd5 / DFA_Careers` (0 HK, board active) |
| Citi | `citi.wd5 / 2` |
| Capital Group | `capgroup.wd1 / capitalgroupcareers` (2 HK, 11 London) |

### Custom scrapers (6 companies)
| Company | Method | Notes |
|---|---|---|
| Goldman Sachs | Custom GraphQL API | `api-higher.gs.com` — full descriptions |
| JPMorgan Chase | Oracle HCM REST API | `jpmc.fa.oraclecloud.com` — ~131 HK jobs |
| Standard Chartered | J2W sitemap | ~112 HK jobs — titles only (JS-rendered site) |
| Millennium Management | Eightfold API | `career.mlp.com` — ~18 HK jobs |
| HSBC | Eightfold API | `hsbc.eightfold.ai` — ~233 HK jobs |
| Schroders | Oracle HCM REST API | `ekbq.fa.em2.oraclecloud.com` — scraped with London filter, 2 HK |

### Workable (1 company)
| Company | Account | Notes |
|---|---|---|
| Capula Investment Management | `capula-investment-management-ltd` | Public widget API, titles/locations only (no description endpoint) — 1 HK role as of Jul 2026 |

### Custom — Framer site (1 company)
| Company | Method | Notes |
|---|---|---|
| Arrowpoint Investment Partners | Static HTML scrape | No ATS/API — titles only, location unconfirmed per-role (small firm, 6 roles across HK/SG/Dubai) |

## Personal Target List Coverage

Cross-referenced against the 81-firm personal target list (`Company_List_Hedge_Funds.csv`, maintained outside this repo). Last checked: **2026-07-26**.

| Status | Count |
|---|---|
| ✅ Tracked (actively scraped) | 33 |
| ✗ Confirmed dead end (no usable public API / no HK office) | 17 |
| ? Not yet researched | 31 |
| **Total target firms** | **81** |

### ✅ Tracked — actively scraped (33)

| Target list name | Platform |
|---|---|
| AQR Capital Management | Greenhouse |
| Arrowpoint Investment Partners (HK) → *Arrowpoint Investment Partners* | Custom (Framer) |
| Barclays → *Barclays Hong Kong* | Workday |
| BlackRock (Aladdin / SAE) → *BlackRock* | Workday |
| Capula Investment Management | Workable |
| Citadel Securities | Greenhouse |
| Citigroup → *Citi* | Workday |
| DRW | Greenhouse |
| Deutsche Bank | Workday |
| Flow Traders | Greenhouse |
| Goldman Sachs → *Goldman Sachs Hong Kong* | Custom GraphQL |
| HSBC → *HSBC Hong Kong* | Eightfold |
| Hudson River Trading | Greenhouse |
| IMC Trading | Greenhouse |
| Interactive Brokers (IBKR) → *Interactive Brokers* | Greenhouse |
| JPMorgan → *JPMorgan Chase Hong Kong* | Oracle HCM |
| Jane Street | Greenhouse |
| Jump Trading | Greenhouse |
| Man Group (AHL) → *Man Group* | Greenhouse |
| Marshall Wace | Greenhouse |
| Millennium Management | Eightfold |
| Morgan Stanley → *Morgan Stanley Hong Kong* | Workday |
| Optiver | Greenhouse |
| Point72 / Cubist → *Point72* | Greenhouse |
| Qube Research (QRT) → *Qube Research & Technologies* | Greenhouse |
| Schonfeld | Greenhouse |
| Squarepoint Capital | Greenhouse |
| Standard Chartered → *Standard Chartered Hong Kong* | J2W sitemap |
| Tower Research Capital | Greenhouse |
| Virtu Financial | Greenhouse |
| Winton Group → *Winton* | Greenhouse |
| WorldQuant | Greenhouse |
| XTX Markets | Greenhouse |

### ✗ Confirmed dead end — don't re-research (17)

| Firm | Reason |
|---|---|
| Citadel | All boards blocked — Greenhouse 404, Lever 404, careers page 403 |
| SIG / Susquehanna | iCIMS (`careers-sig.icims.com`) — no public job-listing API |
| DE Shaw | Workday `deshaw.wd1` — 401, auth required (private board) |
| Two Sigma | Custom site (`careers.twosigma.com`) — no public API, 0 HK jobs in practice |
| Teza Technologies | Confirmed no Hong Kong office (US-only) |
| GSA Capital | Greenhouse `gsacapital` — 10 jobs, all London/NY, 0 HK (rechecked Jul 2026) |
| Balyasny | Workday `bamfunds.wd1` — 401, auth required (private board) |
| Five Rings Capital | Confirmed no Hong Kong office (US-only) |
| Akuna Capital | Greenhouse `akunacapital` — 0 HK jobs (Chicago/Sydney/Singapore only) |
| Headlands Technology | Confirmed no Hong Kong office (US-only) |
| Old Mission Capital | Confirmed no Hong Kong office (Chicago-only) |
| Bank of America | Workday `ghr.wd1/lateral-us` — only a US-only lateral-hires board found, no international board |
| Nomura | Taleo ATS — requires authentication, no public API |
| UBS | No public Workday board found (`ubs.wd3` is a different company); Taleo blocked |
| Exodus Point Capital Management | Greenhouse `exoduspoint` — 2 generic jobs, 0 HK (rechecked Jul 2026) |
| Bridgewater Associates | Lever 404; near-zero HK presence (client relations only) |
| Bloomberg | Workday tenant unclear — found Bloomberg Industry Group's (different affiliate), not LP/Terminal's; needs manual URL discovery |

### ? Not tracked — never researched (31)

Mostly small Chicago-based prop shops with unconfirmed Hong Kong presence. Deprioritized to avoid burning research time on long-shot firms — revisit if one becomes specifically relevant.

| Firm | HK presence (per target list) |
|---|---|
| Amber Group | Yes |
| Mako Trading | Yes |
| All Options | Likely |
| Vatic Labs | Likely |
| Deep Blue Capital | Yes |
| Allston Trading | Likely |
| Da Vinci Trading | Likely |
| Chimera Securities | Yes |
| Matrix Executions | Likely |
| Eclipse Trading | Likely |
| Algorithmic Trading Grp | Uncertain |
| Maverick Derivatives | Likely |
| Wolverine Trading | Likely |
| Belvedere Trading | Likely |
| Geneva Trading | Uncertain |
| Epoch Capital | Uncertain |
| Eagle Seven | Uncertain |
| Grace Hall Trading | Uncertain |
| Market Wizards | Uncertain |
| Prime Trading | Uncertain |
| Quantbox Research | Uncertain |
| Seven Points Capital | Uncertain |
| Valkyrie Trading | Uncertain |
| League Trading | Uncertain |
| Marquette Partners | Uncertain |
| Barak Capital | Uncertain |
| Domstad Traders | Uncertain |
| Genk Capital | Uncertain |
| Chicago Trading Company | Uncertain |
| Liquid Capital Group | Uncertain |
| Z.R.T.X. | Uncertain |

## Project Structure

```
hk-job-aggregator/
├── scrapers/
│   ├── greenhouse_scraper.py          # Greenhouse ATS (23 companies)
│   ├── workday_scraper.py             # Workday (13 companies)
│   ├── goldman_scraper.py             # Goldman Sachs — custom GraphQL
│   ├── jpmorgan_scraper.py            # JPMorgan — Oracle HCM REST
│   ├── standard_chartered_scraper.py  # Standard Chartered — J2W sitemap
│   ├── millennium_scraper.py          # Millennium Management — Eightfold
│   ├── hsbc_scraper.py                # HSBC — Eightfold
│   ├── schroders_scraper.py           # Schroders — Oracle HCM REST
│   ├── workable_scraper.py            # Capula — Workable widget API
│   ├── arrowpoint_scraper.py          # Arrowpoint — custom Framer site scrape
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
| Scraping | Python + Requests, 8 ATS/platform types |
| Database | Supabase (PostgreSQL) via psycopg2 |
| AI Matching | Claude Haiku (`claude-haiku-4-5-20251001`) |
| Email | Gmail SMTP, HTML digest |
| Scheduler | GitHub Actions cron |

## Cost

~$1–3/month (Claude API calls only). GitHub Actions, Supabase, and Gmail are all free tier.
