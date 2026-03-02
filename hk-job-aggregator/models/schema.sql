-- HK Finance Job Monitor — PostgreSQL Schema (Supabase)

-- ============================================
-- 1. COMPANIES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS companies (
    id               SERIAL PRIMARY KEY,
    name             TEXT NOT NULL UNIQUE,
    career_url       TEXT NOT NULL,
    ats_platform     TEXT,                          -- 'Greenhouse', 'Workday', 'Lever', 'Custom'
    industry         TEXT DEFAULT 'Finance',
    location         TEXT DEFAULT 'Hong Kong',
    is_active        BOOLEAN DEFAULT TRUE,
    last_scraped_at  TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    notes            TEXT
);

CREATE INDEX IF NOT EXISTS idx_companies_active      ON companies(is_active);
CREATE INDEX IF NOT EXISTS idx_companies_last_scraped ON companies(last_scraped_at);


-- ============================================
-- 2. JOBS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS jobs (
    id           SERIAL PRIMARY KEY,
    company_id   INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    job_hash     TEXT NOT NULL UNIQUE,              -- sha256[:16] of company_id + title + url
    title        TEXT NOT NULL,
    url          TEXT NOT NULL UNIQUE,
    description  TEXT,
    requirements TEXT,
    location     TEXT,
    job_type     TEXT,                              -- 'Full-time', 'Intern', 'Contract'

    match_score   DOUBLE PRECISION,                -- 0.0–1.0; NULL = not yet scored
    match_reasons JSONB,                           -- ["reason 1", "reason 2"]

    status       TEXT DEFAULT 'new',               -- 'new', 'seen', 'applied', 'archived'
    notified_at  TIMESTAMPTZ,

    posted_date   TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_company     ON jobs(company_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status      ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs(match_score);
CREATE INDEX IF NOT EXISTS idx_jobs_hash        ON jobs(job_hash);
CREATE INDEX IF NOT EXISTS idx_jobs_first_seen  ON jobs(first_seen_at);


-- ============================================
-- 3. PROFILE TABLE (single row)
-- ============================================
CREATE TABLE IF NOT EXISTS profile (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    cv_text          TEXT,
    skills           JSONB,                         -- ["Python", "C++", "Trading"]
    experience_years INTEGER,
    education        TEXT,
    preferences      JSONB,                         -- {"min_salary": 50000}
    match_threshold  DOUBLE PRECISION DEFAULT 0.6,
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO profile (id) VALUES (1) ON CONFLICT DO NOTHING;


-- ============================================
-- 4. SCRAPER LOGS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS scraper_logs (
    id               SERIAL PRIMARY KEY,
    company_id       INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    status           TEXT NOT NULL,                -- 'success', 'failed', 'no_jobs'
    jobs_found       INTEGER DEFAULT 0,
    new_jobs_count   INTEGER DEFAULT 0,
    error_message    TEXT,
    duration_seconds DOUBLE PRECISION,
    scraped_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_company    ON scraper_logs(company_id);
CREATE INDEX IF NOT EXISTS idx_logs_status     ON scraper_logs(status);
CREATE INDEX IF NOT EXISTS idx_logs_scraped_at ON scraper_logs(scraped_at);


-- ============================================
-- VIEWS
-- ============================================

CREATE OR REPLACE VIEW jobs_to_notify AS
SELECT j.id, j.title, c.name AS company, j.url,
       j.match_score, j.match_reasons, j.first_seen_at
FROM jobs j
JOIN companies c ON j.company_id = c.id
WHERE j.status = 'new'
  AND j.match_score >= (SELECT match_threshold FROM profile WHERE id = 1)
  AND j.notified_at IS NULL
ORDER BY j.match_score DESC, j.first_seen_at DESC;


CREATE OR REPLACE VIEW failing_scrapers AS
SELECT c.name, c.career_url, sl.error_message, sl.scraped_at
FROM companies c
JOIN scraper_logs sl ON c.id = sl.company_id
WHERE sl.id IN (
    SELECT MAX(id) FROM scraper_logs GROUP BY company_id
)
AND sl.status = 'failed'
ORDER BY sl.scraped_at DESC;


CREATE OR REPLACE VIEW recent_activity AS
SELECT DATE(first_seen_at) AS date,
       COUNT(*) AS total_jobs,
       COUNT(CASE WHEN match_score >= 0.6 THEN 1 END) AS matching_jobs,
       COUNT(CASE WHEN status = 'new' THEN 1 END) AS unseen_jobs
FROM jobs
WHERE first_seen_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(first_seen_at)
ORDER BY date DESC;
