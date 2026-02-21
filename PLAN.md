# HK Job Aggregator — Plan

## Overview
Automated pipeline: Scrape HK hedge fund jobs → Store in DB → AI match against CV → Email weekly digest

## Architecture
```
GitHub Actions (cron 8am HKT daily)
  → scrape_all.py       — Greenhouse API, 18 companies, HK filter
    → Supabase PostgreSQL  — dedup, store jobs
      → matcher.py      — Claude Haiku, batch 5 jobs/call, pre-filter
        → emailer.py    — HTML digest, Gmail SMTP
```

---

## Phase 1: Database — ✅ DONE
- [x] Supabase project created (PostgreSQL, free tier, ap-northeast-1)
- [x] Schema: `companies`, `jobs`, `profile`, `scraper_logs`, `notifications`
- [x] `models/db.py` — psycopg2, full CRUD, dedup via `job_hash` + `url` UNIQUE
- [x] UniqueViolation handling (URL constraint fallback)
- [x] `update_job_description()` for two-step scrape+describe flow
- [x] `.env` with `DATABASE_URL`

## Phase 2: Scraping — ✅ DONE
- [x] `scrapers/greenhouse_scraper.py` — universal Greenhouse API scraper
- [x] `scrape_all.py` — loops all companies in `GREENHOUSE_TOKENS`, HK filter, dedup, logs
- [x] `seed_companies.py` — 29 companies seeded
- [x] Probed 90+ Greenhouse board tokens, found 18 valid HK hedge fund boards
- [x] HK location filter, rate limiting, per-company error handling
- [x] Structured CI logging (collapsible groups, timestamps, summary table)
- [x] `--no-descriptions` flag for fast daily runs

**Active Greenhouse companies (200+ HK jobs total):**
| Company | Token | HK Jobs |
|---------|-------|---------|
| Jane Street | `janestreet` | 61 |
| Qube Research & Technologies | `quberesearchandtechnologies` | 58 |
| Point72 | `point72` | 20 |
| Squarepoint Capital | `squarepointcapital` | 16 |
| Flow Traders | `flowtraders` | 11 |
| Jump Trading | `jumptrading` | 10 |
| Tower Research Capital | `towerresearchcapital` | 8 |
| Schonfeld | `schonfeld` | 7 |
| IMC Trading | `imc` | 6 |
| Man Group | `mangroup` | 1 |
| WorldQuant | `worldquant` | 1 |
| Graham Capital Management | `grahamcapitalmanagement` | 1 |
| + 6 monitored (0 HK now) | AQR, Marshall Wace, Winton, Akuna, ExodusPoint, PDT | — |

## Phase 3: AI Matching — ✅ BUILT (pending API credits)
- [x] `matcher.py` — Claude Haiku (`claude-haiku-4-5-20251001`)
- [x] Batch scoring: 5 jobs per API call (~80% fewer calls vs 1-by-1)
- [x] Pre-filter by title (seniority + function keywords) — zero API cost
- [x] DB-safe: only saves fully validated results; missing/failed jobs stay `NULL` → retried next run
- [x] Fallback: batch parse failure → individual scoring for that batch
- [x] CV stored at `data/cv.txt`
- [x] `ANTHROPIC_API_KEY` in `.env` and GitHub Secrets
- [ ] **Pending: top up Anthropic credits (~$5) to activate**

**Pre-filter keywords (no API call):**
- Seniority: Senior, Director, VP, MD, Head of, Principal, Partner, Chief
- Function: Payroll, Procurement, Recruiter, HR, Legal, Marketing, Sales, Admin, Facilities

**Cost estimate:** ~$0.05 per full run (200 jobs, batch=5, ~40 API calls)

## Phase 4: Email — ✅ DONE
- [x] `emailer.py` — Gmail SMTP via `smtplib` SSL
- [x] Two-section HTML digest:
  - **AI-Scored Matches** — score badge (green/amber), company, role, reasons, Apply button
  - **New Unscored Jobs** — shown when AI is off/failed, so no posting is ever missed
- [x] Weekly window: only jobs from last 7 days
- [x] `notified_at` set on send — no duplicate emails
- [x] `--dry-run` saves `digest_preview.html` locally
- [x] Gmail App Password configured (`mahirlive2000@gmail.com`)

## Phase 5: GitHub Actions — ✅ DONE
- [x] `.github/workflows/daily-scrape.yml`
- [x] Cron: `0 0 * * *` (midnight UTC = 8am HKT)
- [x] `workflow_dispatch` for manual runs
- [x] Steps: checkout → install → scrape → score (optional) → email
- [x] `continue-on-error: true` on scorer — email always sends even if AI fails
- [x] Warning annotation if scorer fails
- [x] Job summary table on workflow run page
- [ ] **Pending: move secrets from Environment → Repository level on GitHub**

**GitHub Secrets needed:**
| Secret | Value |
|--------|-------|
| `DATABASE_URL` | Supabase connection string |
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `GMAIL_ADDRESS` | mahirlive2000@gmail.com |
| `GMAIL_APP_PASSWORD` | 16-char app password |
| `NOTIFY_EMAIL` | mahirlive2000@gmail.com |

## Phase 6: Future Expansion
- [ ] Workday scraper (Goldman, HSBC, JPMorgan, BofA)
- [ ] Custom scrapers (Citadel Securities, DRW, Barclays)
- [ ] Web dashboard (FastAPI + simple frontend)
- [ ] Job application tracking (applied / interview / offer)
- [ ] Slack or Telegram notifications

---

## Cost (Monthly)
| Service | Cost |
|---------|------|
| Supabase | Free (500MB, 50K rows) |
| GitHub Actions | Free (public repo) |
| Anthropic API | ~$0.05–0.10/day → ~$1.50–3/month |
| Gmail SMTP | Free |
| **Total** | **~$2–3/month** |

## Immediate To-Dos
1. Move GitHub secrets from Environment → Repository level
2. Trigger manual workflow run to test end-to-end
3. Top up Anthropic credits ($5) to activate AI scoring
