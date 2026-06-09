def analyze_skill_gap(
    candidate_skills,
    required_skills
):

    candidate_skills = {
        s.lower()
        for s in candidate_skills
    }

    required_skills = {
        s.lower()
        for s in required_skills
    }

    missing_skills = list(
        required_skills - candidate_skills
    )

    return {
        "missing_skills": missing_skills,
        "gap_count": len(missing_skills)
    }