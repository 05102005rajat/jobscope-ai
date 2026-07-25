from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.auth import verify_api_key
from app.database import init_db
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
def health():
    return {"ok": True}
