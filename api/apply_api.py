from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from database.candidate_repository import get_candidate
from database.mongodb import applications_collection, available_jobs_collection
from skill_gap.advanced_gap_analyzer import analyze_gap
from bson import ObjectId

router = APIRouter()


class ApplyRequest(BaseModel):
    candidate_id: str
    job_id: str


@router.post("/apply", tags=["Apply"])
def apply_for_job(req: ApplyRequest):
    candidate = get_candidate(req.candidate_id)
    if not candidate:
        return {"error": "Candidate not found"}

    try:
        job = available_jobs_collection.find_one({"_id": ObjectId(req.job_id)})
    except Exception:
        job = None
    if not job:
        job = available_jobs_collection.find_one({"hr_job_id": req.job_id})
    if not job:
        return {"error": f"Job not found: {req.job_id}"}

    existing = applications_collection.find_one({
        "candidate_id": req.candidate_id,
        "job_id": str(job["_id"]),
    })
    if existing:
        return {
            "status": "already_applied",
            "message": f"You have already applied for {job.get('title')}.",
            "job_title": job.get("title"),
        }

    gap = analyze_gap(candidate, job)
    cname = candidate.get("personal_info", {}).get("name", "Unknown") \
            if isinstance(candidate.get("personal_info"), dict) else "Unknown"

    application = {
        "candidate_id":    req.candidate_id,
        "candidate_name":  cname,
        "job_id":          str(job["_id"]),
        "job_title":       job.get("title", ""),
        "job_role":        job.get("role", ""),
        "gap_score":       gap["gap_score"],
        "skill_match_pct": gap["skill_match_pct"],
        "is_eligible":     gap["is_eligible"],
        "missing_mandatory": gap["missing_mandatory"],
        "missing_certs":   gap["missing_certs"],
        "present_skills":  gap["present_skills"],
        "applied_at":      datetime.utcnow().isoformat(),
        "status":          "submitted",
    }
    result = applications_collection.insert_one(application)

    msg = (f"Successfully applied for {job.get('title')}! You are a strong match."
           if gap["is_eligible"]
           else f"Applied for {job.get('title')}. Note: you may not fully meet all requirements.")

    return {
        "status":           "applied",
        "application_id":   str(result.inserted_id),
        "job_title":        job.get("title"),
        "candidate_name":   cname,
        "is_eligible":      gap["is_eligible"],
        "skill_match_pct":  gap["skill_match_pct"],
        "missing_mandatory": gap["missing_mandatory"],
        "message":          msg,
    }


@router.get("/apply/{candidate_id}", tags=["Apply"])
def get_applications(candidate_id: str):
    apps = list(applications_collection.find({"candidate_id": candidate_id}))
    for a in apps:
        a["_id"] = str(a["_id"])
    return {"candidate_id": candidate_id, "applications": apps, "count": len(apps)}


@router.get("/hr/applications/{job_id}", tags=["HR Agent"])
def get_job_applications(job_id: str):
    apps = list(applications_collection.find({"job_id": job_id}))
    for a in apps:
        a["_id"] = str(a["_id"])
    return {"job_id": job_id, "applications": apps, "count": len(apps)}
