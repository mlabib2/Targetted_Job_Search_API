# Database Schema

PostgreSQL on Supabase. Four tables, three views.

## Tables

```
┌──────────────────────┐
│      companies       │  One row per target company
│                      │
│  id                  │  SERIAL PK
│  name                │  Unique — must match scrape_all.py dict keys exactly
│  career_url          │  TEXT
│  ats_platform        │  Greenhouse / Workday / Oracle HCM / Custom / etc.
│  notes               │  ATS details, tenant IDs, investigation notes
│  is_active           │  BOOLEAN DEFAULT TRUE
│  last_scraped_at     │  TIMESTAMPTZ
│  created_at          │  TIMESTAMPTZ DEFAULT NOW()
└──────────┬───────────┘
           │ 1:N
┌──────────▼───────────┐
│         jobs         │  All scraped postings
│                      │
│  id                  │  SERIAL PK
│  company_id          │  FK → companies (CASCADE DELETE)
│  job_hash            │  TEXT UNIQUE — sha256[:16](company_id + title + url)
│  title               │  TEXT
│  url                 │  TEXT UNIQUE
│  location            │  TEXT
│  job_type            │  TEXT — 'Full-time', 'Intern', 'Contract'
│  description         │  TEXT — fetched separately for most platforms
│  requirements        │  TEXT
│  match_score         │  DOUBLE PRECISION — 0.0–1.0; NULL = not yet scored
│  match_reasons       │  JSONB — ["reason 1", "reason 2"]
│  status              │  TEXT DEFAULT 'new'
│                      │     new          — freshly scraped, not acted on
│                      │     seen         — reviewed
│                      │     applied      — application submitted
│                      │     interviewing — in interview process
│                      │     offer        — received an offer
│                      │     rejected     — rejected / archived
│  notified_at         │  TIMESTAMPTZ — set when included in email digest
│  posted_date         │  TIMESTAMPTZ — from ATS when available
│  first_seen_at       │  TIMESTAMPTZ DEFAULT NOW()
│  last_seen_at        │  TIMESTAMPTZ DEFAULT NOW() — updated on every scrape
└──────────────────────┘

┌──────────────────────┐
│       profile        │  Single row — your CV and preferences
│                      │
│  id                  │  Always 1 (enforced by CHECK id = 1)
│  cv_text             │  TEXT — not used at runtime; CV is read from data/cv.txt
│  skills              │  JSONB — ["Python", "C++", "Trading"]
│  experience_years    │  INTEGER
│  education           │  TEXT
│  preferences         │  JSONB
│  match_threshold     │  DOUBLE PRECISION DEFAULT 0.6
│  updated_at          │  TIMESTAMPTZ DEFAULT NOW()
└──────────────────────┘

┌──────────────────────┐
│    scraper_logs      │  One row per scrape run per company
│                      │
│  id                  │  SERIAL PK
│  company_id          │  FK → companies (CASCADE DELETE)
│  status              │  success / failed / no_jobs
│  jobs_found          │  INTEGER DEFAULT 0
│  new_jobs_count      │  INTEGER DEFAULT 0
│  error_message       │  TEXT — populated on failure
│  duration_seconds    │  DOUBLE PRECISION
│  scraped_at          │  TIMESTAMPTZ DEFAULT NOW()
└──────────────────────┘
```

## Views

**`jobs_to_notify`** — new jobs above match threshold, not yet emailed:
```sql
SELECT * FROM jobs_to_notify;
-- id, title, company, url, match_score, match_reasons, first_seen_at
```

**`failing_scrapers`** — companies whose last scrape failed:
```sql
SELECT * FROM failing_scrapers;
-- name, career_url, error_message, scraped_at
```

**`recent_activity`** — 7-day scraping summary:
```sql
SELECT * FROM recent_activity;
-- date, total_jobs, matching_jobs, unseen_jobs
```

## Key Decisions

**Deduplication** — `job_hash = sha256[:16](company_id + title.lower() + url)`. URL also has a UNIQUE constraint as a secondary guard. Title changes on an existing URL are treated as duplicates (no re-score).

**Descriptions** — stored as plain text after `strip_html()`. Some platforms (Goldman GraphQL) return description inline; others (Greenhouse, Workday, JPMorgan) require a second API call per new job — fetched selectively for new jobs only with a 0.3 s rate-limit delay. Standard Chartered descriptions are unavailable (JS-rendered site — scraped via sitemap, titles only).

**Notifications** — `notified_at` is set when a job is included in an email digest. Jobs with `notified_at IS NULL AND match_score >= threshold AND status = 'new'` are the email queue. Running `emailer.py` sets `notified_at` for everything it sends.

**Application status** — the `status` column doubles as both a scraper lifecycle flag (`new` / `seen`) and an application tracker (`applied` / `interviewing` / `offer` / `rejected`). Use `track.py` to update status from the CLI. Jobs with status `applied` or later are excluded from the email digest's "unscored" fallback table.

**Company names** — the `name` column in `companies` must match the dictionary keys in `scrape_all.py` exactly (case-sensitive). This is the join between the scraper config and the DB.
