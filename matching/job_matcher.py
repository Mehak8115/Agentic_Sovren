# matching/job_matcher.py

from matching.skill_similarity import (
    skills_match
)


def calculate_match(
    candidate_skills,
    required_skills
):

    matched_skills = []
    missing_skills = []

    candidate_skills = [
        str(skill).strip()
        for skill in candidate_skills
        if skill
    ]

    required_skills = [
        str(skill).strip()
        for skill in required_skills
        if skill
    ]

    for required in required_skills:

        matched = False

        for candidate in candidate_skills:

            try:

                if skills_match(
                    candidate,
                    required
                ):

                    matched_skills.append(
                        required
                    )

                    matched = True
                    break

            except Exception as e:

                print(
                    f"Error matching "
                    f"{candidate} -> {required}"
                )

                print(e)

        if not matched:

            missing_skills.append(
                required
            )

    score = 0

    if len(required_skills) > 0:

        score = round(
            (
                len(matched_skills)
                /
                len(required_skills)
            ) * 100,
            2
        )

    return {

        "match_score":
        score,

        "matched_skills":
        matched_skills,

        "missing_skills":
        missing_skills
    }