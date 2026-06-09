from rapidfuzz import fuzz


def normalize_skills(skills):

    normalized = []

    for skill in skills:

        if isinstance(skill, list):

            for s in skill:

                normalized.append(
                    str(s).strip().lower()
                )

        else:

            normalized.append(
                str(skill).strip().lower()
            )

    return normalized


def semantic_skill_match(
    candidate_skills,
    required_skills,
    threshold=75
):

    matched = []

    missing = []

    candidate_skills = normalize_skills(
        candidate_skills
    )

    required_skills = normalize_skills(
        required_skills
    )

    for req in required_skills:

        best_score = 0

        for cand in candidate_skills:

            score = fuzz.token_sort_ratio(
                req,
                cand
            )

            best_score = max(
                best_score,
                score
            )

        if best_score >= threshold:

            matched.append(req)

        else:

            missing.append(req)

    return matched, missing