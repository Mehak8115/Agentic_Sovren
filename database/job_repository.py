from database.mongodb import jobs_collection

def get_job_by_title(title):

    return jobs_collection.find_one(
        {
            "title": {
                "$regex": f"^{title}$",
                "$options": "i"
            }
        }
    )


def get_all_jobs():
    return list(jobs_collection.find())
    
