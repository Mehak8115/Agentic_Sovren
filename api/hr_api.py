# api/hr_api.py

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from agents.hr_agent import HRAgent
from database.hr_repository import get_all_hr_jobs, get_hr_job

router   = APIRouter()
hr_agent = HRAgent()


# ── Generate JD ───────────────────────────────────────────────────────────────

class GenerateJDRequest(BaseModel):
    role:             str  = Field(..., example="Chief Officer")
    location:         str  = Field(..., example="Mumbai")
    experience_years: int  = Field(default=3, example=3)
    extra_context:    str  = Field(default="", example="Bulk carrier operations")
    include_thought_process: bool = False

@router.post("/hr/generate-jd", tags=["HR Agent"])
def generate_jd(req: GenerateJDRequest):
    return hr_agent.run(
        query="generate job description",
        role=req.role, location=req.location,
        experience_years=req.experience_years,
        extra_context=req.extra_context,
        include_thought_process=req.include_thought_process,
    )


# ── Rank Candidates ───────────────────────────────────────────────────────────

class RankRequest(BaseModel):
    job_id: str = Field(..., example="<hr_job_id>")
    include_thought_process: bool = False

@router.post("/hr/rank-candidates", tags=["HR Agent"])
def rank_candidates(req: RankRequest):
    return hr_agent.run(
        query="rank candidates",
        job_id=req.job_id,
        include_thought_process=req.include_thought_process,
    )


# ── Skill Gap: candidate vs job ───────────────────────────────────────────────

class SkillGapRequest(BaseModel):
    candidate_id: str = Field(..., example="<candidate_id>")
    job_id:       str = Field(..., example="<hr_job_id>")
    include_thought_process: bool = False

@router.post("/hr/skill-gap", tags=["HR Agent"])
def hr_skill_gap(req: SkillGapRequest):
    return hr_agent.run(
        query="skill gap analysis",
        candidate_id=req.candidate_id,
        job_id=req.job_id,
        include_thought_process=req.include_thought_process,
    )


# ── Recruitment Report ────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    job_id: str = Field(..., example="<hr_job_id>")
    include_thought_process: bool = False

@router.post("/hr/recruitment-report", tags=["HR Agent"])
def recruitment_report(req: ReportRequest):
    return hr_agent.run(
        query="recruitment report",
        job_id=req.job_id,
        include_thought_process=req.include_thought_process,
    )


# ── Interview Summary ─────────────────────────────────────────────────────────

class InterviewRequest(BaseModel):
    candidate_name:   str = Field(..., example="John Smith")
    job_title:        str = Field(..., example="Chief Officer")
    interview_notes:  str = Field(..., example="Candidate showed strong navigation skills...")
    interview_rating: int = Field(default=3, ge=1, le=5)
    job_id:           Optional[str] = None
    include_thought_process: bool = False

@router.post("/hr/interview-summary", tags=["HR Agent"])
def interview_summary(req: InterviewRequest):
    return hr_agent.run(
        query="interview summary",
        candidate_name=req.candidate_name,
        job_title=req.job_title,
        interview_notes=req.interview_notes,
        interview_rating=req.interview_rating,
        job_id=req.job_id or "",
        include_thought_process=req.include_thought_process,
    )


# ── Publish / Close Job ───────────────────────────────────────────────────────

@router.post("/hr/jobs/{job_id}/publish", tags=["HR Agent"])
def publish_job(job_id: str):
    return hr_agent.run(query="publish job", job_id=job_id)

@router.post("/hr/jobs/{job_id}/close", tags=["HR Agent"])
def close_job(job_id: str):
    return hr_agent.run(query="close job", job_id=job_id)


# ── List HR Jobs ──────────────────────────────────────────────────────────────

@router.get("/hr/jobs", tags=["HR Agent"])
def list_hr_jobs(status: Optional[str] = None):
    jobs = get_all_hr_jobs(status)
    return {"jobs": jobs, "count": len(jobs)}

@router.get("/hr/jobs/{job_id}", tags=["HR Agent"])
def get_job(job_id: str):
    job = get_hr_job(job_id)
    if not job:
        return {"error": "Job not found"}
    return job
