# database/hr_repository.py

from database.mongodb import db
from database.candidate_repository import get_all_candidates
from bson import ObjectId
from copy import deepcopy
from datetime import datetime

hr_jobs_collection        = db["hr_jobs"]
interview_logs_collection = db["interview_logs"]


# ── HR Job CRUD ────────────────────────────────────────────────────────────────

def save_hr_job(job: dict) -> str:
    data = deepcopy(job)
    data["created_at"] = datetime.utcnow().isoformat()
    data["status"]     = data.get("status", "draft")   # draft | published | closed
    result = hr_jobs_collection.insert_one(data)
    return str(result.inserted_id)


def get_hr_job(job_id: str) -> dict | None:
    doc = hr_jobs_collection.find_one({"_id": ObjectId(job_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


def get_all_hr_jobs(status: str | None = None) -> list[dict]:
    query = {"status": status} if status else {}
    jobs  = list(hr_jobs_collection.find(query))
    for j in jobs:
        j["_id"] = str(j["_id"])
    return jobs


def publish_hr_job(job_id: str) -> bool:
    """Publish HR job → copies it to available_jobs so crew can see it."""
    from database.mongodb import available_jobs_collection

    job = get_hr_job(job_id)
    if not job:
        return False

    # Update status in hr_jobs
    hr_jobs_collection.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": {"status": "published", "published_at": datetime.utcnow().isoformat()}}
    )

    # Build clean job data without the _id field (let MongoDB assign its own)
    job_data = {k: v for k, v in job.items() if k != "_id"}
    job_data["hr_job_id"] = job_id
    job_data["status"]    = "published"

    # Upsert by hr_job_id — if already exists update it, else insert
    available_jobs_collection.update_one(
        {"hr_job_id": job_id},
        {"$set": job_data},
        upsert=True,
    )
    return True


def close_hr_job(job_id: str) -> bool:
    from database.mongodb import available_jobs_collection
    hr_jobs_collection.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": {"status": "closed"}}
    )
    available_jobs_collection.update_one(
        {"hr_job_id": job_id},
        {"$set": {"status": "closed"}}
    )
    return True


# ── Interview logs ─────────────────────────────────────────────────────────────

def save_interview_log(log: dict) -> str:
    data = deepcopy(log)
    data["created_at"] = datetime.utcnow().isoformat()
    result = interview_logs_collection.insert_one(data)
    return str(result.inserted_id)


def get_interview_logs(job_id: str) -> list[dict]:
    logs = list(interview_logs_collection.find({"job_id": job_id}))
    for l in logs:
        l["_id"] = str(l["_id"])
    return logs


# ── Candidates ─────────────────────────────────────────────────────────────────

def get_candidates_for_ranking() -> list[dict]:
    candidates = get_all_candidates()
    result = []
    for c in candidates:
        c["_id"] = str(c["_id"])
        result.append(c)
    return result
