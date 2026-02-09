from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/hk_jobs")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id_hash = Column(String, unique=True, index=True)  # For deduplication
    title = Column(String, index=True)
    company = Column(String, index=True)
    location = Column(String)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String, default="HKD")
    description = Column(Text)
    requirements = Column(Text, nullable=True)
    job_type = Column(String)  # Full-time, Part-time, Contract, Internship
    experience_level = Column(String)  # Entry, Mid, Senior
    source = Column(String)  # JobsDB, CTgoodjobs, LinkedIn, Indeed
    source_url = Column(String, unique=True)
    posted_date = Column(DateTime, index=True)
    scraped_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    company_info = relationship("Company", back_populates="jobs")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    industry = Column(String, nullable=True)
    size = Column(String, nullable=True)  # 1-10, 11-50, 51-200, etc.
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    website = Column(String, nullable=True)

    # Enrichment data
    funding_stage = Column(String, nullable=True)  # Seed, Series A, etc.
    total_funding = Column(Float, nullable=True)
    tech_stack = Column(Text, nullable=True)  # JSON array as text
    glassdoor_rating = Column(Float, nullable=True)

    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    jobs = relationship("Job", back_populates="company_info")


class UserTracking(Base):
    __tablename__ = "user_tracking"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # For future multi-user support
    job_id = Column(Integer, ForeignKey("jobs.id"))
    status = Column(String)  # saved, applied, interviewing, rejected, offer
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
