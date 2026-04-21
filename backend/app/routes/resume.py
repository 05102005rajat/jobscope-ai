from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, Resume
from app.utils.resume_parser import extract_text_from_pdf, extract_skills
import json

router = APIRouter()


@router.post("/resume")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    raw_text = extract_text_from_pdf(content)
    skills = extract_skills(raw_text)

    db_resume = Resume(
        filename=file.filename,
        raw_text=raw_text,
        skills=json.dumps(skills),
    )
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)

    return {
        "id": db_resume.id,
        "filename": db_resume.filename,
        "skills_found": skills,
        "text_length": len(raw_text),
    }


@router.get("/resume/latest")
def get_latest_resume(db: Session = Depends(get_db)):
    resume = db.query(Resume).order_by(Resume.uploaded_date.desc()).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume uploaded yet")
    return {
        "id": resume.id,
        "filename": resume.filename,
        "skills": json.loads(resume.skills) if resume.skills else [],
        "uploaded_date": resume.uploaded_date,
    }
