# # candidate_repositiory

from copy import deepcopy
from database.mongodb import candidates_collection
from bson import ObjectId


def get_candidate(candidate_id):

    return candidates_collection.find_one(
        {"_id": ObjectId(candidate_id)}
    )


def get_all_candidates():

    return list(
        candidates_collection.find({})
    )


def save_candidate(profile, resume_path):

    data = deepcopy(profile)

    data["resume_path"] = resume_path

    result = candidates_collection.insert_one(
        data
    )

    return str(
        result.inserted_id
    )