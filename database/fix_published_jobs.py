"""
One-time fix: sync all published HR jobs into available_jobs
Run from project root: python -m database.fix_published_jobs
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient

client  = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
db      = client["sovren"]
hr_jobs = db["hr_jobs"]
avail   = db["available_jobs"]

published = list(hr_jobs.find({"status": "published"}))
print(f"Found {len(published)} published HR jobs to sync...")

fixed = 0
for job in published:
    job_id   = str(job["_id"])
    job_data = {k: v for k, v in job.items() if k != "_id"}
    job_data["hr_job_id"] = job_id
    job_data["status"]    = "published"

    avail.update_one(
        {"hr_job_id": job_id},
        {"$set": job_data},
        upsert=True,
    )
    fixed += 1
    print(f"  + {job.get('title')} | {job.get('location')}")

total = avail.count_documents({"hr_job_id": {"$exists": True}})
print(f"\nDone. {fixed} jobs synced. HR jobs in available_jobs: {total}")
client.close()
