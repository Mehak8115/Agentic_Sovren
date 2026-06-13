"""Fix null status in available_jobs"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pymongo import MongoClient

db = MongoClient("mongodb://localhost:27017")["sovren"]
r  = db.available_jobs.update_many({"status": None}, {"$set": {"status": "published"}})
print(f"Fixed {r.modified_count} jobs with null status → published")
total = db.available_jobs.count_documents({"status": {"$nin": ["closed"]}})
print(f"Total available jobs (non-closed): {total}")
