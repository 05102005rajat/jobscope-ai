from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class JobCreate(BaseModel):
    company: str
    role: str
    status: str = "applied"
    url: Optional[str] = None
    jd_text: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    notes: Optional[str] = None


class JobUpdate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    url: Optional[str] = None
    jd_text: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    notes: Optional[str] = None


class JobResponse(BaseModel):
    id: int
    company: str
    role: str
    status: str
    url: Optional[str]
    jd_text: Optional[str]
    location: Optional[str]
    salary: Optional[str]
    notes: Optional[str]
    match_score: Optional[float]
    missing_skills: Optional[str]
    applied_date: datetime
    updated_date: datetime

    class Config:
        from_attributes = True


class AnalyzeRequest(BaseModel):
    jd_text: str
    job_id: Optional[int] = None


class AnalyzeResponse(BaseModel):
    match_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    suggestions: list[str]


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class StatsResponse(BaseModel):
    total_applications: int
    by_status: dict
    interview_rate: float
    response_rate: float
    avg_match_score: Optional[float]
    top_missing_skills: list[str]
