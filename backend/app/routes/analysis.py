from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, Resume, Job, Analysis
from app.models import AnalyzeRequest, AnalyzeResponse
from app.utils.jd_parser import extract_jd_skills
from app.utils.matcher import compare as compare_skills
import json

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_jd(request: AnalyzeRequest, db: Session = Depends(get_db)):
    resume = db.query(Resume).order_by(Resume.uploaded_date.desc()).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    resume_skills = json.loads(resume.skills) if resume.skills else []
    jd_skills = extract_jd_skills(request.jd_text)

    result = compare_skills(
        resume_skills=resume_skills,
        jd_skills=jd_skills,
        resume_text=resume.raw_text,
        jd_text=request.jd_text,
    )

    matched = result["matched"]
    missing = result["missing"]
    suggestions = result["suggestions"]
    total = len(matched) + len(missing)
    match_score = round(len(matched) / total * 100, 1) if total > 0 else 0.0

    analysis = Analysis(
        job_id=request.job_id or 0,
        resume_id=resume.id,
        match_score=match_score,
        matched_skills=json.dumps(matched),
        missing_skills=json.dumps(missing),
        suggestions=json.dumps(suggestions),
    )
    db.add(analysis)

    if request.job_id:
        job = db.query(Job).filter(Job.id == request.job_id).first()
        if job:
            job.match_score = match_score
            job.missing_skills = json.dumps(missing)

    db.commit()

    return AnalyzeResponse(
        match_score=match_score,
        matched_skills=matched,
        missing_skills=missing,
        suggestions=suggestions,
    )
