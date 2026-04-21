from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    status = Column(String(50), default="applied")  # applied, interview, offer, rejected
    url = Column(Text, nullable=True)
    jd_text = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    salary = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    match_score = Column(Float, nullable=True)
    missing_skills = Column(Text, nullable=True)  # JSON string of missing skills
    applied_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    skills = Column(Text, nullable=True)  # JSON string of extracted skills
    uploaded_date = Column(DateTime, default=datetime.utcnow)


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, nullable=False)
    resume_id = Column(Integer, nullable=False)
    match_score = Column(Float, nullable=True)
    matched_skills = Column(Text, nullable=True)  # JSON
    missing_skills = Column(Text, nullable=True)  # JSON
    suggestions = Column(Text, nullable=True)  # JSON
    created_date = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
