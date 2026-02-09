# Database Schema Overview

Clean, minimal schema for HK Job Monitor. SQLite-based, optimized for 20-50 companies.

## Entity Relationship

```
┌──────────────┐
│  COMPANIES   │  Your target list (Goldman, Jane Street, etc.)
│              │
│ • name       │
│ • career_url │
│ • ats_platform (Workday/Greenhouse/Custom)
│ • last_scraped_at
└──────┬───────┘
       │
       │ 1:N
       │
┌──────▼───────┐
│     JOBS     │  All scraped postings
│              │
│ • job_hash   │  (deduplication key)
│ • title      │
│ • url        │
│ • description│
│ • match_score│  (0.0 - 1.0)
│ • status     │  (new/seen/applied)
│ • notified_at│
└──────────────┘


┌──────────────┐
│   PROFILE    │  Your CV/skills (single row)
│              │
│ • cv_text    │
│ • skills     │  JSON: ["Python", "C++", "Trading"]
│ • embedding  │  Vector for matching
│ • match_threshold (default: 0.6)
└──────────────┘


┌──────────────┐
│SCRAPER_LOGS  │  Health monitoring
│              │
│ • company_id │
│ • status     │  (success/failed)
│ • jobs_found │
│ • new_jobs_count
│ • error_message
└──────────────┘
```

## Key Design Decisions

### 1. **Job Deduplication**
- Uses `job_hash = sha256(company_id + title + url)`
- Prevents duplicate notifications for same job
- Updates `last_seen_at` when job re-appears (still active)

### 2. **Status Flow**
```
new → seen → applied → (archived)
 ↑      ↑       ↑
 └──────┴───────┴─── User actions
```

- `new`: Just scraped, not yet notified or user hasn't seen
- `seen`: User has been notified or manually marked seen
- `applied`: User applied to this job
- `archived`: Job no longer relevant

### 3. **Match Scoring**
- Jobs get scored 0.0 to 1.0 based on CV similarity
- Only jobs with `score >= match_threshold` (default 0.6) trigger notifications
- `match_reasons` JSON stores why it matched: `["Python", "Trading experience"]`

### 4. **Scraper Health**
- Every scrape is logged with status
- `failing_scrapers` view shows companies that failed last run
- Alert user if scraper fails

### 5. **Notification Tracking**
- `notified_at` timestamp prevents re-notifying about same job
- `notifications` table tracks email/WhatsApp sends (optional)

## Indexes

Optimized for common queries:
- `idx_jobs_status` - Fast filtering by new/seen
- `idx_jobs_match_score` - Quick retrieval of high-match jobs
- `idx_jobs_hash` - Fast deduplication checks
- `idx_companies_active` - Only query active companies

## Views (Convenience)

### `jobs_to_notify`
Jobs that match threshold and haven't been sent yet:
```sql
SELECT * FROM jobs_to_notify;
-- Returns: title, company, url, match_score, match_reasons
```

### `failing_scrapers`
Companies whose scrapers are broken:
```sql
SELECT * FROM failing_scrapers;
-- Returns: company name, error, last attempt
```

### `recent_activity`
7-day summary of scraping activity:
```sql
SELECT * FROM recent_activity;
-- Returns: date, total_jobs, matching_jobs, unseen_jobs
```

## Usage Examples

```python
from models.db import get_db

# Initialize
db = get_db()

# Add company
company_id = db.add_company(
    name="Goldman Sachs HK",
    career_url="https://...",
    ats_platform="Workday"
)

# Add job (auto-deduplicates)
job_id = db.add_job(
    company_id=company_id,
    title="Software Engineer - Trading Systems",
    url="https://...",
    description="..."
)

# Update match score
db.update_job_match(
    job_id=job_id,
    match_score=0.85,
    match_reasons=["Python", "Trading", "Low-latency"]
)

# Get jobs to notify
jobs = db.get_jobs_to_notify()
for job in jobs:
    print(f"{job['title']} at {job['company']} - {job['match_score']:.0%} match")
    # Send notification...
    db.mark_job_notified(job['id'])

# Log scraper run
db.log_scrape(
    company_id=company_id,
    status='success',
    jobs_found=25,
    new_jobs=3,
    duration=2.5
)

# Check health
failing = db.get_failing_scrapers()
if failing:
    print(f"⚠️ {len(failing)} scrapers are failing!")
```

## Elegant Features

1. **Single profile row** - Uses `CHECK (id = 1)` constraint
2. **Auto timestamps** - `CURRENT_TIMESTAMP` defaults
3. **Cascading deletes** - Remove company → removes all its jobs
4. **Dict-like rows** - `row_factory = sqlite3.Row` for clean access
5. **Context manager** - `with get_db() as db:` auto-closes connection
6. **Type safety** - All operations use parameterized queries (SQL injection safe)

## Storage Estimates

For 50 companies over 1 year:
- 50 companies × 10 jobs/company × 365 scrapes = ~180K jobs
- Average job: ~2KB (title, description, etc.)
- **Total: ~360MB** - easily fits in SQLite's limits (140TB max)

SQLite is perfect for this scale.
