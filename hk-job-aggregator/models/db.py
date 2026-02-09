"""
Clean database interface for HK Job Monitor
Uses SQLite with proper abstractions
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import pickle


class JobDatabase:
    """Main database interface"""

    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_db()

    def _init_db(self):
        """Initialize database with schema"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return dict-like rows

        # Check if database is already initialized
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies'")

        if not cursor.fetchone():
            # Database not initialized, run schema
            schema_path = Path(__file__).parent / "schema.sql"
            with open(schema_path) as f:
                self.conn.executescript(f.read())
            self.conn.commit()

    def get_connection(self):
        """Get database connection"""
        if self.conn is None:
            self._init_db()
        return self.conn

    # ============================================
    # COMPANY OPERATIONS
    # ============================================

    def add_company(self, name: str, career_url: str, ats_platform: str = None, notes: str = None) -> int:
        """Add a new company to monitor"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO companies (name, career_url, ats_platform, notes)
            VALUES (?, ?, ?, ?)
        """, (name, career_url, ats_platform, notes))
        self.conn.commit()
        return cursor.lastrowid

    def get_active_companies(self) -> List[Dict]:
        """Get all active companies to scrape"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM companies
            WHERE is_active = 1
            ORDER BY name
        """)
        return [dict(row) for row in cursor.fetchall()]

    def update_company_scraped(self, company_id: int):
        """Update last_scraped_at timestamp"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE companies
            SET last_scraped_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (company_id,))
        self.conn.commit()

    # ============================================
    # JOB OPERATIONS
    # ============================================

    def add_job(self, company_id: int, title: str, url: str,
                description: str = None, **kwargs) -> Optional[int]:
        """
        Add a new job (if not duplicate)
        Returns job_id if new, None if duplicate
        """
        # Generate hash for deduplication
        job_hash = self._generate_job_hash(company_id, title, url)

        # Check if exists
        if self.job_exists(job_hash):
            # Update last_seen_at
            self.conn.execute("""
                UPDATE jobs SET last_seen_at = CURRENT_TIMESTAMP
                WHERE job_hash = ?
            """, (job_hash,))
            self.conn.commit()
            return None

        # Insert new job
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO jobs (
                company_id, job_hash, title, url, description,
                location, job_type, requirements, posted_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id, job_hash, title, url, description,
            kwargs.get('location'),
            kwargs.get('job_type'),
            kwargs.get('requirements'),
            kwargs.get('posted_date')
        ))
        self.conn.commit()
        return cursor.lastrowid

    def job_exists(self, job_hash: str) -> bool:
        """Check if job already exists"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM jobs WHERE job_hash = ? LIMIT 1", (job_hash,))
        return cursor.fetchone() is not None

    def update_job_match(self, job_id: int, match_score: float, match_reasons: List[str]):
        """Update job matching score and reasons"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE jobs
            SET match_score = ?, match_reasons = ?
            WHERE id = ?
        """, (match_score, json.dumps(match_reasons), job_id))
        self.conn.commit()

    def mark_job_notified(self, job_id: int):
        """Mark job as notified"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE jobs
            SET notified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (job_id,))
        self.conn.commit()

    def get_jobs_to_notify(self) -> List[Dict]:
        """Get jobs that match threshold and haven't been notified"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM jobs_to_notify")
        return [dict(row) for row in cursor.fetchall()]

    def mark_job_seen(self, job_id: int):
        """Mark job as seen"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE jobs SET status = 'seen' WHERE id = ?
        """, (job_id,))
        self.conn.commit()

    # ============================================
    # PROFILE OPERATIONS
    # ============================================

    def update_profile(self, cv_text: str = None, skills: List[str] = None,
                      embedding: bytes = None, **kwargs):
        """Update user profile"""
        updates = []
        params = []

        if cv_text:
            updates.append("cv_text = ?")
            params.append(cv_text)
        if skills:
            updates.append("skills = ?")
            params.append(json.dumps(skills))
        if embedding:
            updates.append("embedding = ?")
            params.append(embedding)
        if 'experience_years' in kwargs:
            updates.append("experience_years = ?")
            params.append(kwargs['experience_years'])

        updates.append("updated_at = CURRENT_TIMESTAMP")

        query = f"UPDATE profile SET {', '.join(updates)} WHERE id = 1"
        self.conn.execute(query, params)
        self.conn.commit()

    def get_profile(self) -> Dict:
        """Get user profile"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM profile WHERE id = 1")
        row = cursor.fetchone()
        if row:
            profile = dict(row)
            # Parse JSON fields
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
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO scraper_logs
            (company_id, status, jobs_found, new_jobs_count, error_message, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (company_id, status, jobs_found, new_jobs, error, duration))
        self.conn.commit()

    def get_failing_scrapers(self) -> List[Dict]:
        """Get companies whose scrapers are failing"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM failing_scrapers")
        return [dict(row) for row in cursor.fetchall()]

    # ============================================
    # ANALYTICS
    # ============================================

    def get_stats(self) -> Dict:
        """Get overall statistics"""
        cursor = self.conn.cursor()

        # Total counts
        cursor.execute("SELECT COUNT(*) FROM companies WHERE is_active = 1")
        total_companies = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'new'")
        new_jobs = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM jobs
            WHERE match_score >= (SELECT match_threshold FROM profile WHERE id = 1)
            AND status = 'new'
        """)
        matching_jobs = cursor.fetchone()[0]

        cursor.execute("SELECT * FROM recent_activity")
        recent = [dict(row) for row in cursor.fetchall()]

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
    # Test database
    with get_db() as db:
        print("Database initialized successfully!")
        print(f"Stats: {db.get_stats()}")
