# api/agent_api.py

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from groq import RateLimitError

from agents.supervisor_agent import SupervisorAgent
from parser.resume_extractor import extract_resume_text

router = APIRouter()
agent  = SupervisorAgent()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Request model for JSON body ───────────────────────────────────────────────

class AgentRequest(BaseModel):
    query:                   str
    candidate_id:            Optional[str] = None
    include_thought_process: bool          = False


# ── Route 1: JSON body with candidate_id (candidate already in DB) ─────────────

@router.post(
    "/agent/run",
    summary="Run agent with existing candidate ID",
)
def run_agent(request: AgentRequest):
    try:
        return agent.run(
            query=request.query,
            candidate_id=request.candidate_id,
            include_thought_process=request.include_thought_process,
        )
    except RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="AI model rate limit reached. All available models are busy — please wait a few minutes and try again.",
        )


# ── Route 2: File upload — parse resume + run agent in one shot ───────────────

@router.post(
    "/agent/run-with-resume",
    summary="Upload resume + run agent (no prior candidate_id needed)",
)
async def run_agent_with_resume(
    query:                   str  = Form(...),
    file:                    UploadFile = File(...),
    save_candidate:          bool = Form(False),
    include_thought_process: bool = Form(False),
):
    # Save uploaded file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Extract text from PDF / DOCX
    resume_text = extract_resume_text(file_path)

    try:
        return agent.run(
            query=query,
            resume_text=resume_text,
            save_candidate=save_candidate,
            include_thought_process=include_thought_process,
        )
    except RateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail="AI model rate limit reached. All available models are busy — please wait a few minutes and try again.",
        )
