from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ChatRequest, ChatResponse
from app.agent.graph import run_agent

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        response = run_agent(request.message, db)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent failed: {e}") from e
    return ChatResponse(response=response)
