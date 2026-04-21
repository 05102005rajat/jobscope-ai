from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db, Job
from app.models import JobCreate, JobUpdate, JobResponse, StatsResponse
import json

router = APIRouter()


@router.get("/jobs", response_model=list[JobResponse])
def get_jobs(
    status: str = None,
    company: str = None,
    db: Session = Depends(get_db),
):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))
    return query.order_by(Job.applied_date.desc()).all()


@router.post("/jobs", response_model=JobResponse)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    db_job = Job(**job.model_dump())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


@router.put("/jobs/{job_id}", response_model=JobResponse)
def update_job(job_id: int, job: JobUpdate, db: Session = Depends(get_db)):
    db_job = db.query(Job).filter(Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    for key, value in job.model_dump(exclude_unset=True).items():
        setattr(db_job, key, value)
    db.commit()
    db.refresh(db_job)
    return db_job


@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    db_job = db.query(Job).filter(Job.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(db_job)
    db.commit()
    return {"message": "Job deleted"}


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Job).count()
    if total == 0:
        return StatsResponse(
            total_applications=0,
            by_status={},
            interview_rate=0.0,
            response_rate=0.0,
            avg_match_score=None,
            top_missing_skills=[],
        )

    status_counts = dict(
        db.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
    )

    interviews = status_counts.get("interview", 0) + status_counts.get("offer", 0)
    responses = total - status_counts.get("applied", 0)

    avg_score = db.query(func.avg(Job.match_score)).filter(Job.match_score.isnot(None)).scalar()

    # Aggregate missing skills across all jobs
    all_missing = []
    jobs_with_skills = db.query(Job.missing_skills).filter(Job.missing_skills.isnot(None)).all()
    for (skills_json,) in jobs_with_skills:
        try:
            skills = json.loads(skills_json)
            all_missing.extend(skills)
        except (json.JSONDecodeError, TypeError):
            pass

    # Count and sort missing skills
    skill_counts = {}
    for skill in all_missing:
        skill_counts[skill] = skill_counts.get(skill, 0) + 1
    top_missing = sorted(skill_counts, key=skill_counts.get, reverse=True)[:10]

    return StatsResponse(
        total_applications=total,
        by_status=status_counts,
        interview_rate=interviews / total if total > 0 else 0.0,
        response_rate=responses / total if total > 0 else 0.0,
        avg_match_score=round(avg_score, 2) if avg_score else None,
        top_missing_skills=top_missing,
    )
