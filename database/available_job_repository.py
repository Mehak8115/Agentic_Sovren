# available_job_repository

from database.mongodb import (
    available_jobs_collection
)

def get_all_available_jobs():
    return list(
        available_jobs_collection.find({})
    )