from pymongo import MongoClient


client = MongoClient(
    "mongodb://localhost:27017",
    serverSelectionTimeoutMS=5000
)

client.admin.command("ping")

db = client["sovren"]

candidates_collection = db["candidates"]
jobs_collection = db["jobs"]
applications_collection = db["applications"]
available_jobs_collection = db["available_jobs"]

print("MongoDB Connected Successfully")

