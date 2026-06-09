# from fastapi import APIRouter

# from database.candidate_repository import get_candidate
# from database.job_repository import get_job_by_title

# from skill_gap.role_analyzer import analyze_role_fit
# from database.mongodb import jobs_collection
# router = APIRouter()


# @router.get(
#     "/role-analysis/{candidate_id}/{job_title}",
#     summary="Skill Gap Analysis",
#     description="""
#     Analyze how well a candidate fits a target role.

#     Example:
#     Engineer
#     Captain
#     Navigator
#     Deckhand
#     Medic

#     Returns:
#     - Readiness score
#     - Missing skills
#     - Missing experience
#     - Improvement recommendations

#     Example URL:
#     /role-analysis/{candidate_id}/Engineer
#     """
# )
# def role_analysis(
#     candidate_id,
#     job_title
# ):

#     candidate = get_candidate(
#         candidate_id
#     )

#     if not candidate:

#         return {
#             "error": "Candidate not found"
#         }

#     job = jobs_collection.find_one({
#     "title": {
#         "$regex": f"^{job_title}$",
#         "$options": "i"
#     }
# })

#     if not job:

#         return {
#             "error": "Job not found"
#         }

#     result = analyze_role_fit(
#         candidate,
#         job
#     )

#     return {

#         "candidate":
#         candidate["personal_info"]["name"],

#         "target_role":
#         job["title"],

#         **result
#     }


from fastapi import APIRouter

from database.candidate_repository import (
    get_candidate
)

from database.job_repository import (
    get_job_by_title
)

from skill_gap.advanced_gap_analyzer import (
    analyze_gap
)

router = APIRouter()


@router.get(
    "/skill-gap/{candidate_id}/{role}"
)
def skill_gap(
    candidate_id,
    role
):

    candidate = get_candidate(
        candidate_id
    )

    if not candidate:

        return {
            "error":
            "Candidate not found"
        }

    job = get_job_by_title(
        role
    )

    if not job:

        return {
            "error":
            "Role not found"
        }

    return analyze_gap(
        candidate,
        job
    )