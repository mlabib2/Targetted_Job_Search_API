-- HK Finance Job Monitor - Database Schema
-- SQLite optimized, minimal and elegant

-- ============================================
-- 1. COMPANIES TABLE
-- Target companies to monitor
-- ============================================
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    career_url TEXT NOT NULL,
    ats_platform TEXT, -- 'Greenhouse', 'Workday', 'Lever', 'Custom', etc.
    industry TEXT DEFAULT 'Finance',
    location TEXT DEFAULT 'Hong Kong',
    is_active BOOLEAN DEFAULT 1, -- Can pause monitoring for specific companies
    last_scraped_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Metadata
    notes TEXT -- e.g., "High priority", "Referral contact: John Doe"
);

CREATE INDEX idx_companies_active ON companies(is_active);
CREATE INDEX idx_companies_last_scraped ON companies(last_scraped_at);


-- ============================================
-- 2. JOBS TABLE
-- All scraped job postings
-- ============================================
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,

    -- Job Details
    job_hash TEXT NOT NULL UNIQUE, -- For deduplication: hash(company + title + url)
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    description TEXT,
    requirements TEXT,
    location TEXT,
    job_type TEXT, -- 'Full-time', 'Intern', 'Contract'

    -- Matching
    match_score REAL, -- 0.0 to 1.0 (60%+ triggers notification)
    match_reasons TEXT, -- JSON: ["Python match", "Trading experience"]

    -- Status Tracking
    status TEXT DEFAULT 'new', -- 'new', 'seen', 'applied', 'archived'
    notified_at DATETIME, -- When user was notified

    -- Timestamps
    posted_date DATETIME, -- When job was posted (from job board)
    first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- When we first scraped it
    last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- Last time we saw it (for expiry detection)

    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE INDEX idx_jobs_company ON jobs(company_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_match_score ON jobs(match_score);
CREATE INDEX idx_jobs_hash ON jobs(job_hash);
CREATE INDEX idx_jobs_first_seen ON jobs(first_seen_at);


-- ============================================
-- 3. USER PROFILE TABLE
-- Your CV/skills for matching (single row)
-- ============================================
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1), -- Only one profile allowed

    -- CV Data
    cv_text TEXT, -- Full CV text
    skills TEXT, -- JSON array: ["Python", "C++", "Trading", "React"]
    experience_years INTEGER,
    education TEXT,
    preferences TEXT, -- JSON: {"min_salary": 50000, "job_types": ["Full-time"]}

    -- Matching Config
    embedding BLOB, -- OpenAI embedding vector (serialized)
    match_threshold REAL DEFAULT 0.6, -- 60% match threshold

    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Insert default profile
INSERT OR IGNORE INTO profile (id) VALUES (1);


-- ============================================
-- 4. SCRAPER LOGS TABLE
-- Health monitoring and debugging
-- ============================================
CREATE TABLE IF NOT EXISTS scraper_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,

    -- Scrape Results
    status TEXT NOT NULL, -- 'success', 'failed', 'no_jobs'
    jobs_found INTEGER DEFAULT 0,
    new_jobs_count INTEGER DEFAULT 0,
    error_message TEXT,

    -- Performance
    duration_seconds REAL,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE INDEX idx_logs_company ON scraper_logs(company_id);
CREATE INDEX idx_logs_status ON scraper_logs(status);
CREATE INDEX idx_logs_scraped_at ON scraper_logs(scraped_at);


-- ============================================
-- 5. NOTIFICATIONS TABLE (Optional but useful)
-- Track what we've sent to avoid duplicates
-- ============================================
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    channel TEXT NOT NULL, -- 'email', 'whatsapp', 'telegram'
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent', -- 'sent', 'failed', 'bounced'

    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE INDEX idx_notifications_job ON notifications(job_id);
CREATE INDEX idx_notifications_sent_at ON notifications(sent_at);


-- ============================================
-- VIEWS (for easy querying)
-- ============================================

-- New jobs that need notification
CREATE VIEW IF NOT EXISTS jobs_to_notify AS
SELECT
    j.id,
    j.title,
    c.name AS company,
    j.url,
    j.match_score,
    j.match_reasons,
    j.first_seen_at
FROM jobs j
JOIN companies c ON j.company_id = c.id
WHERE j.status = 'new'
  AND j.match_score >= (SELECT match_threshold FROM profile WHERE id = 1)
  AND j.notified_at IS NULL
ORDER BY j.match_score DESC, j.first_seen_at DESC;


-- Scraper health check (companies that failed last scrape)
CREATE VIEW IF NOT EXISTS failing_scrapers AS
SELECT
    c.name,
    c.career_url,
    sl.error_message,
    sl.scraped_at
FROM companies c
JOIN scraper_logs sl ON c.id = sl.company_id
WHERE sl.id IN (
    SELECT MAX(id)
    FROM scraper_logs
    GROUP BY company_id
)
AND sl.status = 'failed'
ORDER BY sl.scraped_at DESC;


-- Recent activity summary
CREATE VIEW IF NOT EXISTS recent_activity AS
SELECT
    DATE(first_seen_at) AS date,
    COUNT(*) AS total_jobs,
    COUNT(CASE WHEN match_score >= 0.6 THEN 1 END) AS matching_jobs,
    COUNT(CASE WHEN status = 'new' THEN 1 END) AS unseen_jobs
FROM jobs
WHERE first_seen_at >= DATE('now', '-7 days')
GROUP BY DATE(first_seen_at)
ORDER BY date DESC;
