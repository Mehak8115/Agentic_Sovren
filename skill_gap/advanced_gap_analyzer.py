# advanced_gap_analyzer
from matching.skill_similarity import (
    skills_match
)


def analyze_gap(
    candidate,
    job
):

    candidate_skills = candidate.get(
        "skills",
        []
    )

    mandatory = job.get(
        "mandatory_skills",
        []
    )

    optional = job.get(
        "optional_skills",
        []
    )

    matched_mandatory = []
    matched_optional = []

    missing_mandatory = []
    missing_optional = []

    for skill in mandatory:

        found = False

        for candidate_skill in candidate_skills:

            if skills_match(
                candidate_skill,
                skill
            ):

                matched_mandatory.append(
                    skill
                )

                found = True
                break

        if not found:

            missing_mandatory.append(
                skill
            )

    for skill in optional:

        found = False

        for candidate_skill in candidate_skills:

            if skills_match(
                candidate_skill,
                skill
            ):

                matched_optional.append(
                    skill
                )

                found = True
                break

        if not found:

            missing_optional.append(
                skill
            )

    # Skill match: based on MANDATORY skills only
    # Optional skills give a small bonus but don't inflate the base score
    mandatory_match_pct = round(
        (len(matched_mandatory) / max(len(mandatory), 1)) * 100, 1
    )

    optional_bonus = round(
        (len(matched_optional) / max(len(optional), 1)) * 10, 1
    ) if optional else 0

    skill_match_pct = min(mandatory_match_pct + optional_bonus, 100.0)
    skill_match_pct = round(skill_match_pct, 1)

    candidate_certs = {
        str(c).lower()
        for c in candidate.get(
            "certifications",
            []
        )
    }

    required_certs = {
        str(c).lower()
        for c in job.get(
            "required_certifications",
            []
        )
    }

    present_certs = list(
        candidate_certs.intersection(
            required_certs
        )
    )

    missing_certs = list(
        required_certs
        -
        candidate_certs
    )

    exp_years = candidate.get(
        "experience_years",
        0
    )

    min_exp = job.get(
        "minimum_experience",
        0
    )

    exp_score = min(
        (
            exp_years
            /
            max(min_exp, 1)
        ) * 100,
        100
    )

    cert_score = 100

    if len(required_certs) > 0:
        cert_score = round(
            (len(present_certs) / len(required_certs)) * 100, 1
        )

    # Gap score formula:
    # 40% skills (mandatory-based), 30% experience, 30% certifications
    # Missing certs apply a hard penalty on top
    raw_score = (
        skill_match_pct * 0.40
        + exp_score      * 0.30
        + cert_score     * 0.30
    )

    # Additional penalty: each missing mandatory cert deducts 5 points
    cert_penalty = len(missing_certs) * 5
    gap_score = round(max(raw_score - cert_penalty, 0), 1)

    eligible = (
        len(missing_mandatory) <= 4
        and exp_years >= min_exp
    )

    if gap_score >= 70:
        label = "Excellent match"

    elif gap_score >= 50:
        label = "Good match"

    elif gap_score >= 30:
        label = "Partial match"

    else:
        label = "Not suitable"

    return {

        "role":
        job["title"].lower(),

        "skill_match_pct":
        skill_match_pct,

        "gap_score":
        gap_score,

        "is_eligible":
        eligible,

        "eligibility_label":
        label,

        "present_skills":
        matched_mandatory
        +
        matched_optional,

        "missing_mandatory":
        missing_mandatory,

        "missing_optional":
        missing_optional,

        "present_certs":
        present_certs,

        "missing_certs":
        missing_certs,

        "experience_years":
        exp_years,

        "summary":
        f"{skill_match_pct}% skill match | "
        f"gap score {gap_score}/100 | "
        f"missing {len(missing_mandatory)} mandatory skill(s) | "
        f"missing {len(missing_certs)} certification(s) | "
        f"exp {exp_years}/{min_exp} yrs"
    }