"""
Clean database interface for HK Job Monitor
Uses PostgreSQL (Supabase) with psycopg2
"""

import psycopg2
import psycopg2.extras
import json
import hashlib
import os
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class JobDatabase:
    """Main database interface"""

    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL not set in environment or argument")
        self.conn = None
        self._connect()

    def _connect(self):
        """Connect to PostgreSQL"""
        self.conn = psycopg2.connect(self.database_url)
        self.conn.autocommit = True

    def _cursor(self):
        """Get a dict cursor"""
        return self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # ============================================
    # COMPANY OPERATIONS
    # ============================================

    def add_company(self, name: str, career_url: str, ats_platform: str = None, notes: str = None) -> int:
        """Add a new company to monitor"""
        cur = self._cursor()
        cur.execute("""
            INSERT INTO companies (name, career_url, ats_platform, notes)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (name, career_url, ats_platform, notes))
        return cur.fetchone()['id']

    def get_active_companies(self) -> List[Dict]:
        """Get all active companies to scrape"""
        cur = self._cursor()
        cur.execute("""
            SELECT * FROM companies
            WHERE is_active = TRUE
            ORDER BY name
        """)
        return [dict(row) for row in cur.fetchall()]

    def get_company_by_name(self, name: str) -> Optional[Dict]:
        """Get a company by name"""
        cur = self._cursor()
        cur.execute("SELECT * FROM companies WHERE name = %s", (name,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_company_scraped(self, company_id: int):
        """Update last_scraped_at timestamp"""
        cur = self._cursor()
        cur.execute("""
            UPDATE companies
            SET last_scraped_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (company_id,))

    # ============================================
    # JOB OPERATIONS
    # ============================================

    def add_job(self, company_id: int, title: str, url: str,
                description: str = None, **kwargs) -> Optional[int]:
        """
        Add a new job (if not duplicate)
        Returns job_id if new, None if duplicate
        """
        job_hash = self._generate_job_hash(company_id, title, url)

        if self.job_exists(job_hash):
            cur = self._cursor()
            cur.execute("""
                UPDATE jobs SET last_seen_at = CURRENT_TIMESTAMP
                WHERE job_hash = %s
            """, (job_hash,))
            return None

        cur = self._cursor()
        cur.execute("""
            INSERT INTO jobs (
                company_id, job_hash, title, url, description,
                location, job_type, requirements, posted_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            company_id, job_hash, title, url, description,
            kwargs.get('location'),
            kwargs.get('job_type'),
            kwargs.get('requirements'),
            kwargs.get('posted_date')
        ))
        return cur.fetchone()['id']

    def job_exists(self, job_hash: str) -> bool:
        """Check if job already exists"""
        cur = self._cursor()
        cur.execute("SELECT 1 FROM jobs WHERE job_hash = %s LIMIT 1", (job_hash,))
        return cur.fetchone() is not None

    def update_job_match(self, job_id: int, match_score: float, match_reasons: List[str]):
        """Update job matching score and reasons"""
        cur = self._cursor()
        cur.execute("""
            UPDATE jobs
            SET match_score = %s, match_reasons = %s
            WHERE id = %s
        """, (match_score, json.dumps(match_reasons), job_id))

    def mark_job_notified(self, job_id: int):
        """Mark job as notified"""
        cur = self._cursor()
        cur.execute("""
            UPDATE jobs
            SET notified_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (job_id,))

    def get_jobs_to_notify(self) -> List[Dict]:
        """Get jobs that match threshold and haven't been notified"""
        cur = self._cursor()
        cur.execute("""
            SELECT j.id, j.title, c.name AS company, j.url,
                   j.match_score, j.match_reasons, j.first_seen_at
            FROM jobs j
            JOIN companies c ON j.company_id = c.id
            WHERE j.status = 'new'
              AND j.match_score >= (SELECT match_threshold FROM profile WHERE id = 1)
              AND j.notified_at IS NULL
            ORDER BY j.match_score DESC, j.first_seen_at DESC
        """)
        return [dict(row) for row in cur.fetchall()]

    def mark_job_seen(self, job_id: int):
        """Mark job as seen"""
        cur = self._cursor()
        cur.execute("UPDATE jobs SET status = 'seen' WHERE id = %s", (job_id,))

    def get_new_jobs(self) -> List[Dict]:
        """Get all new unscored jobs"""
        cur = self._cursor()
        cur.execute("""
            SELECT j.*, c.name AS company_name
            FROM jobs j
            JOIN companies c ON j.company_id = c.id
            WHERE j.status = 'new' AND j.match_score IS NULL
            ORDER BY j.first_seen_at DESC
        """)
        return [dict(row) for row in cur.fetchall()]

    # ============================================
    # PROFILE OPERATIONS
    # ============================================

    def update_profile(self, cv_text: str = None, skills: List[str] = None,
                       embedding: bytes = None, **kwargs):
        """Update user profile"""
        updates = []
        params = []

        if cv_text:
            updates.append("cv_text = %s")
            params.append(cv_text)
        if skills:
            updates.append("skills = %s")
            params.append(json.dumps(skills))
        if embedding:
            updates.append("embedding = %s")
            params.append(embedding)
        if 'experience_years' in kwargs:
            updates.append("experience_years = %s")
            params.append(kwargs['experience_years'])

        updates.append("updated_at = CURRENT_TIMESTAMP")

        query = f"UPDATE profile SET {', '.join(updates)} WHERE id = 1"
        cur = self._cursor()
        cur.execute(query, params)

    def get_profile(self) -> Dict:
        """Get user profile"""
        cur = self._cursor()
        cur.execute("SELECT * FROM profile WHERE id = 1")
        row = cur.fetchone()
        if row:
            profile = dict(row)
            if profile.get('skills'):
                profile['skills'] = json.loads(profile['skills'])
            if profile.get('preferences'):
                profile['preferences'] = json.loads(profile['preferences'])
            return profile
        return {}

    # ============================================
    # LOGGING OPERATIONS
    # ============================================

    def log_scrape(self, company_id: int, status: str, jobs_found: int = 0,
                   new_jobs: int = 0, error: str = None, duration: float = None):
        """Log scraper run"""
        cur = self._cursor()
        cur.execute("""
            INSERT INTO scraper_logs
            (company_id, status, jobs_found, new_jobs_count, error_message, duration_seconds)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (company_id, status, jobs_found, new_jobs, error, duration))

    def get_failing_scrapers(self) -> List[Dict]:
        """Get companies whose scrapers are failing"""
        cur = self._cursor()
        cur.execute("""
            SELECT c.name, c.career_url, sl.error_message, sl.scraped_at
            FROM companies c
            JOIN scraper_logs sl ON c.id = sl.company_id
            WHERE sl.id IN (
                SELECT MAX(id) FROM scraper_logs GROUP BY company_id
            )
            AND sl.status = 'failed'
            ORDER BY sl.scraped_at DESC
        """)
        return [dict(row) for row in cur.fetchall()]

    # ============================================
    # ANALYTICS
    # ============================================

    def get_stats(self) -> Dict:
        """Get overall statistics"""
        cur = self._cursor()

        cur.execute("SELECT COUNT(*) AS cnt FROM companies WHERE is_active = TRUE")
        total_companies = cur.fetchone()['cnt']

        cur.execute("SELECT COUNT(*) AS cnt FROM jobs WHERE status = 'new'")
        new_jobs = cur.fetchone()['cnt']

        cur.execute("""
            SELECT COUNT(*) AS cnt FROM jobs
            WHERE match_score >= (SELECT match_threshold FROM profile WHERE id = 1)
            AND status = 'new'
        """)
        matching_jobs = cur.fetchone()['cnt']

        cur.execute("""
            SELECT DATE(first_seen_at) AS date,
                   COUNT(*) AS total_jobs,
                   COUNT(CASE WHEN match_score >= 0.6 THEN 1 END) AS matching_jobs,
                   COUNT(CASE WHEN status = 'new' THEN 1 END) AS unseen_jobs
            FROM jobs
            WHERE first_seen_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(first_seen_at)
            ORDER BY date DESC
        """)
        recent = [dict(row) for row in cur.fetchall()]

        return {
            'total_companies': total_companies,
            'new_jobs': new_jobs,
            'matching_jobs': matching_jobs,
            'recent_activity': recent
        }

    # ============================================
    # HELPERS
    # ============================================

    def _generate_job_hash(self, company_id: int, title: str, url: str) -> str:
        """Generate unique hash for job deduplication"""
        unique_string = f"{company_id}:{title.lower().strip()}:{url}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Convenience function
def get_db() -> JobDatabase:
    """Get database instance"""
    return JobDatabase()


if __name__ == "__main__":
    with get_db() as db:
        print("Database connected successfully!")
        print(f"Stats: {db.get_stats()}")
