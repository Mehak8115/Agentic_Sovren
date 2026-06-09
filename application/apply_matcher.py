# from database.job_repository import get_all_jobs
# from database.available_job_repository import (
#     get_all_available_jobs
# )

# def apply_for_jobs(candidate):

#     candidate_skills = [
#         skill.lower()
#         for skill in candidate.get("skills", [])
#     ]

#     candidate_certs = [
#         cert.lower()
#         for cert in candidate.get("certifications", [])
#     ]

#     candidate_exp = candidate.get(
#         "experience_years",
#         0
#     )

#     results = []

#     # jobs = get_all_jobs()
#     jobs = get_all_available_jobs()

#     for job in jobs:

#         mandatory = [
#             skill.lower()
#             for skill in job["mandatory_skills"]
#         ]

#         matched = [
#             skill
#             for skill in mandatory
#             if skill in candidate_skills
#         ]

#         skill_match_pct = round(
#             len(matched) / len(mandatory) * 100,
#             2
#         )

#         missing_skills = [
#             skill
#             for skill in mandatory
#             if skill not in candidate_skills
#         ]

#         missing_certs = [
#             cert
#             for cert in job["required_certifications"]
#             if cert.lower() not in candidate_certs
#         ]

#         experience_ok = (
#             candidate_exp >=
#             job["minimum_experience"]
#         )

#         eligible = (
#             skill_match_pct >= 50
#             and experience_ok
#         )

#         results.append({

#             "job_title":
#             job["title"],

#             "skill_match_pct":
#             skill_match_pct,

#             "eligible":
#             eligible,

#             "missing_skills":
#             missing_skills,

#             "missing_certifications":
#             missing_certs,

#             "required_experience":
#             job["minimum_experience"]
#         })

#     results.sort(
#         key=lambda x: x["skill_match_pct"],
#         reverse=True
#     )

#     return results



# apply_matcher.py

from database.available_job_repository import (
    get_all_available_jobs
)


def normalize_certifications(certifications):

    result = []

    for cert in certifications:

        if isinstance(cert, str):

            result.append(
                cert.lower().strip()
            )

        elif isinstance(cert, dict):

            name = (
                cert.get("name")
                or cert.get("title")
                or cert.get("certificate")
                or ""
            )

            if name:

                result.append(
                    name.lower().strip()
                )

    return result


def apply_for_jobs(candidate):

    candidate_skills = [

        str(skill).lower().strip()

        for skill in candidate.get(
            "skills",
            []
        )
    ]

    candidate_certs = normalize_certifications(

        candidate.get(
            "certifications",
            []
        )

    )

    candidate_exp = candidate.get(
        "experience_years",
        0
    )

    jobs = get_all_available_jobs()

    results = []

    for job in jobs:

        mandatory_skills = [

            skill.lower().strip()

            for skill in job.get(
                "mandatory_skills",
                []
            )
        ]

        matched_skills = [

            skill

            for skill in mandatory_skills

            if skill in candidate_skills
        ]

        skill_match_pct = round(

            (
                len(matched_skills)
                /
                max(
                    len(mandatory_skills),
                    1
                )
            )
            * 100,

            2
        )

        missing_skills = [

            skill

            for skill in mandatory_skills

            if skill not in candidate_skills
        ]

        required_certs = [

            cert.lower().strip()

            for cert in job.get(
                "required_certifications",
                []
            )
        ]

        missing_certs = [

            cert

            for cert in required_certs

            if cert not in candidate_certs
        ]

        experience_ok = (

            candidate_exp >=
            job.get(
                "minimum_experience",
                0
            )
        )

        eligible = (

            skill_match_pct >= 50

            and

            experience_ok
        )

        results.append({

            "job_id":
            str(job.get("_id", "")),

            "job_title":
            job.get("title"),

            "role":
            job.get("role"),

            "skill_match_pct":
            skill_match_pct,

            "eligible":
            eligible,

            "missing_skills":
            missing_skills,

            "missing_certifications":
            missing_certs,

            "required_experience":
            job.get(
                "minimum_experience",
                0
            )
        })

    results.sort(

        key=lambda x: (

            x["eligible"],

            x["skill_match_pct"]

        ),

        reverse=True
    )

    return results