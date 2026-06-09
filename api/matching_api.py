from fastapi import APIRouter

from database.job_repository import get_all_jobs
from database.candidate_repository import get_candidate

from matching.job_matcher import calculate_match

router = APIRouter()


@router.get(
    "/match-jobs/{candidate_id}",
    summary="Find Matching Jobs",
    description="""
    Matches a candidate profile against all available maritime jobs.

    Returns:
    - Match percentage
    - Matched skills
    - Missing skills
    - Experience requirements

    Example roles:
    Captain, Navigator, Engineer, Medic, Deckhand, Steward
    """
)
def match_jobs(candidate_id):

    candidate = get_candidate(candidate_id)

    if not candidate:
        return {
            "error": "Candidate not found"
        }

    candidate_skills = candidate.get(
        "skills",
        []
    )

    print("\nCANDIDATE SKILLS:")
    print(candidate_skills)

    jobs = get_all_jobs()

    results = []

    for job in jobs:

        required_skills = (
            job.get("mandatory_skills", [])
            +
            job.get("optional_skills", [])
        )

        match = calculate_match(
            candidate_skills,
            required_skills
        )

        print("\nJOB:", job["title"])
        print("REQUIRED:", required_skills)
        print("MATCHED:", match["matched_skills"])
        print("SCORE:", match["match_score"])

        results.append({
            "job_title": job["title"],
            "match_score": match["match_score"],
            "matched_skills": match["matched_skills"],
            "missing_skills": match["missing_skills"],
            "minimum_experience": job.get(
                "minimum_experience",
                0
            )
        })

    results.sort(
        key=lambda x: x["match_score"],
        reverse=True
    )

    return results