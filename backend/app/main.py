from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routes import jobs, analysis, chat, resume

app = FastAPI(
    title="JobScope AI",
    description="AI-powered job application tracker with LangGraph agent",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://jobscope-ai.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(resume.router, prefix="/api", tags=["Resume"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"message": "JobScope AI API is running"}
