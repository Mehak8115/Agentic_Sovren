# skill_similarity.py

from rapidfuzz import fuzz


def skills_match(
    skill1,
    skill2
):

    skill1 = str(skill1).strip().lower()
    skill2 = str(skill2).strip().lower()

    if not skill1 or not skill2:
        return False

    # exact match
    if skill1 == skill2:
        return True

    ratio = (
        fuzz.ratio(
            skill1,
            skill2
        ) / 100
    )

    partial_ratio = (
        fuzz.partial_ratio(
            skill1,
            skill2
        ) / 100
    )

    token_sort_ratio = (
        fuzz.token_sort_ratio(
            skill1,
            skill2
        ) / 100
    )

    fuzzy_score = max(
        ratio,
        partial_ratio,
        token_sort_ratio
    )

    return fuzzy_score >= 0.70