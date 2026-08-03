from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import verify_api_key
from app.database import get_db, init_db
from app.routes import jobs, analysis, chat, resume

app = FastAPI(
    title="JobScope AI",
    description="AI-powered job application tracker with LangGraph agent",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api", tags=["Jobs"], dependencies=[Depends(verify_api_key)])
app.include_router(resume.router, prefix="/api", tags=["Resume"], dependencies=[Depends(verify_api_key)])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"], dependencies=[Depends(verify_api_key)])
app.include_router(chat.router, prefix="/api", tags=["Chat"], dependencies=[Depends(verify_api_key)])


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"message": "JobScope AI API is running"}


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    """Actually touches Postgres so uptime pings keep Supabase's free-tier
    project from auto-pausing, instead of just confirming the container is up.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unreachable: {exc}") from exc
    return {"ok": True, "db": "reachable"}
