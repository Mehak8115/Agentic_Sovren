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

    total_required = (
        len(mandatory)
        +
        len(optional)
    )

    matched_total = (
        len(matched_mandatory)
        +
        len(matched_optional)
    )

    skill_match_pct = round(
        (
            matched_total
            /
            total_required
        ) * 100,
        1
    )

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

        cert_score = (
            len(present_certs)
            /
            len(required_certs)
        ) * 100

    gap_score = round(
        (
            skill_match_pct * 0.4
            +
            cert_score * 0.2
            +
            exp_score * 0.4
        ),
        1
    )

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
        f"missing {len(missing_certs)} certification(s)"
    }