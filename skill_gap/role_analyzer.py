from matching.skill_utils import (
    semantic_skill_match
)

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

    return set(normalized)

def analyze_role_fit(candidate, job):

    candidate_skills = normalize_skills(
    candidate.get("skills", [])
)

    required_skills = normalize_skills(
    job["required_skills"]
)

    matched_skills, missing_skills = (
    semantic_skill_match(
        candidate_skills,
        mandatory_skills
    )
)

    skill_score = round(
        (len(matched_skills) /
        len(required_skills)) * 100,
        2
    )

    candidate_exp = candidate.get(
        "experience_years",
        0
    )

    required_exp = job[
        "minimum_experience"
    ]

    experience_score = min(
        (candidate_exp / required_exp) * 100,
        100
    )

    candidate_certs = {
        c.lower()
        for c in candidate.get(
            "certifications",
            []
        )
    }

    required_certs = {
        c.lower()
        for c in job.get(
            "required_certifications",
            []
        )
    }

    matched_certs = list(
        candidate_certs.intersection(
            required_certs
        )
    )

    missing_certs = list(
        required_certs - candidate_certs
    )

    if len(required_certs) > 0:
        cert_score = (
            len(matched_certs)
            /
            len(required_certs)
        ) * 100
    else:
        cert_score = 100

    overall_score = round(
        (skill_score * 0.5)
        +
        (experience_score * 0.3)
        +
        (cert_score * 0.2),
        2
    )

    return {
        "overall_score": overall_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "certification_score": cert_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "missing_certifications": missing_certs,
        "experience_gap": max(
            required_exp - candidate_exp,
            0
        )
    }