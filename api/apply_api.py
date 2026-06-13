from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from database.candidate_repository import get_candidate
from database.mongodb import applications_collection, available_jobs_collection, db
from skill_gap.advanced_gap_analyzer import analyze_gap
from bson import ObjectId

router = APIRouter()
hr_notifications_collection = db["hr_notifications"]


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

    # Block applications with score < 50
    if gap["gap_score"] < 50:
        return {
            "error": f"Your match score ({gap['gap_score']}/100) is below the minimum required (50). Improve your skills and certifications before applying."
        }
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
        "applied_at":      datetime.utcnow().isoformat() + "Z",
        "status":          "submitted",
    }
    result = applications_collection.insert_one(application)

    # Notify HR team about the new application
    hr_notifications_collection.insert_one({
        "type":            "new_application",
        "candidate_id":    req.candidate_id,
        "candidate_name":  cname,
        "job_id":          str(job["_id"]),
        "job_title":       job.get("title", ""),
        "gap_score":       gap["gap_score"],
        "skill_match_pct": gap["skill_match_pct"],
        "is_eligible":     gap["is_eligible"],
        "created_at":      datetime.utcnow().isoformat() + "Z",
        "read":            False,
    })

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


@router.get("/hr/notifications", tags=["HR Agent"])
def get_hr_notifications(unread_only: bool = False):
    query = {"read": False} if unread_only else {}
    notifs = list(hr_notifications_collection.find(query).sort("created_at", -1).limit(50))
    for n in notifs:
        n["_id"] = str(n["_id"])
    return {"notifications": notifs, "count": len(notifs)}


@router.post("/hr/notifications/{notif_id}/read", tags=["HR Agent"])
def mark_notification_read(notif_id: str):
    hr_notifications_collection.update_one(
        {"_id": ObjectId(notif_id)},
        {"$set": {"read": True}}
    )
    return {"status": "ok"}


@router.get("/hr/candidate/{candidate_id}", tags=["HR Agent"])
def get_candidate_profile(candidate_id: str):
    """HR views a candidate's full parsed resume."""
    candidate = get_candidate(candidate_id)
    if not candidate:
        return {"error": "Candidate not found"}
    candidate["_id"] = str(candidate["_id"])
    return candidate
