# agents/crew_tools.py

from database.candidate_repository import get_candidate, save_candidate
from database.available_job_repository import get_all_available_jobs
from skill_gap.advanced_gap_analyzer import analyze_gap
from parser.candidate_parser import parse_resume as llm_parse_resume


# ── Tools ─────────────────────────────────────────────────────────────────────

def tool_parse_resume(candidate_id: str) -> dict | None:
    """Fetch candidate document from MongoDB by ID."""
    return get_candidate(candidate_id)


def tool_parse_resume_from_text(resume_text: str, save: bool = False) -> dict | None:
    """
    Parse raw resume text via LLM and optionally save to DB.
    Returns candidate profile dict (with _id if saved).
    """
    profile = llm_parse_resume(resume_text)
    if not profile:
        return None
    if save:
        inserted_id = save_candidate(profile, resume_path="")
        profile["_id"] = inserted_id
    return profile


def tool_extract_skills(candidate: dict) -> dict:
    """Normalise and deduplicate skills + certifications."""
    skills = sorted({str(s).strip() for s in candidate.get("skills", []) if s})
    certs  = sorted({str(c).strip().lower() for c in candidate.get("certifications", []) if c})
    return {
        "skills":           skills,
        "certifications":   certs,
        "experience_years": candidate.get("experience_years", 0),
    }


def tool_search_jobs() -> list[dict]:
    """Fetch all available maritime job postings."""
    return get_all_available_jobs()


def tool_certification_check(candidate: dict, job: dict) -> dict:
    """Cert-only gap check for a single job."""
    c_certs = {str(c).strip().lower() for c in candidate.get("certifications", [])}
    r_certs = {str(c).strip().lower() for c in job.get("required_certifications", [])}
    present = list(c_certs & r_certs)
    missing = list(r_certs - c_certs)
    score   = round(len(present) / len(r_certs) * 100, 1) if r_certs else 100.0
    return {"present_certs": present, "missing_certs": missing, "cert_score": score}


def tool_crew_gap_analysis(candidate: dict, job: dict) -> dict:
    """Full gap analysis (skills + exp + certs) for one candidate-job pair."""
    result                      = analyze_gap(candidate, job)
    result["job_id"]            = str(job.get("_id", ""))
    result["job_title"]         = job.get("title", "")
    result["salary"]            = job.get("salary", "")
    result["location"]          = job.get("location", "")
    result["minimum_experience"] = job.get("minimum_experience", 0)
    return result


def tool_rank_jobs(gap_results: list[dict]) -> list[dict]:
    """Rank: eligible jobs first, then by gap_score descending."""
    return sorted(
        gap_results,
        key=lambda x: (x.get("is_eligible", False), x.get("gap_score", 0)),
        reverse=True,
    )


def tool_generate_recommendations(gap_results: list[dict]) -> list[dict]:
    """Attach prioritised learning recommendations to each gap result."""
    for result in gap_results:
        recs = []
        for skill in result.get("missing_mandatory", []):
            recs.append({"type": "skill", "priority": "high", "action": f"Learn {skill}"})
        for skill in result.get("missing_optional", []):
            recs.append({"type": "skill", "priority": "low",  "action": f"Learn {skill} (optional)"})
        for cert in result.get("missing_certs", []):
            recs.append({"type": "certification", "priority": "high", "action": f"Complete certification: {cert}"})
        result["recommendations"] = recs
    return gap_results


def tool_build_response(candidate: dict, ranked_results: list[dict], intent: str) -> dict:
    """
    Build structured data payload shaped to the intent.
    intent options: suggest_jobs | skill_gap | career_plan | full_analysis
    """
    name = (
        candidate.get("personal_info", {}).get("name", "Unknown")
        if isinstance(candidate.get("personal_info"), dict)
        else "Unknown"
    )
    eligible = [r for r in ranked_results if r.get("is_eligible")]
    top5     = ranked_results[:5]

    base = {
        "candidate_name": name,
        "intent":         intent,
        "total_jobs":     len(ranked_results),
        "eligible_jobs":  len(eligible),
    }

    if intent == "suggest_jobs":
        base["best_matches"] = [
            {
                "title":             r.get("job_title"),
                "job_id":            r.get("job_id", ""),
                "gap_score":         r.get("gap_score"),
                "is_eligible":       r.get("is_eligible"),
                "eligibility_label": r.get("eligibility_label"),
                "skill_match_pct":   r.get("skill_match_pct"),
                "salary":            r.get("salary", ""),
                "location":          r.get("location", ""),
                "minimum_experience": r.get("minimum_experience"),
                "experience_years":  r.get("experience_years"),
                "summary":           r.get("summary"),
            }
            for r in top5
        ]

    elif intent == "skill_gap":
        base["skill_gap_report"] = [
            {
                "title":             r.get("job_title"),
                "job_id":            r.get("job_id", ""),
                "skill_match_pct":   r.get("skill_match_pct"),
                "missing_mandatory": r.get("missing_mandatory"),
                "missing_optional":  r.get("missing_optional"),
                "missing_certs":     r.get("missing_certs"),
                "present_skills":    r.get("present_skills"),
                "salary":            r.get("salary", ""),
                "location":          r.get("location", ""),
                "minimum_experience": r.get("minimum_experience"),
                "experience_years":  r.get("experience_years"),
                "is_eligible":       r.get("is_eligible"),
                "recommendations":   r.get("recommendations", []),
            }
            for r in top5
        ]

    elif intent == "career_plan":
        all_missing_skills = list({s for r in top5 for s in r.get("missing_mandatory", [])})
        all_missing_certs  = list({c for r in top5 for c in r.get("missing_certs", [])})
        base["career_improvement_plan"] = {
            "top_opportunities": [
                {
                    "title":             r.get("job_title"),
                    "gap_score":         r.get("gap_score"),
                    "is_eligible":       r.get("is_eligible"),
                    "eligibility_label": r.get("eligibility_label"),
                }
                for r in top5
            ],
            "priority_skills_to_learn": all_missing_skills,
            "priority_certs_to_obtain": all_missing_certs,
            "recommended_actions": [
                rec
                for r in top5
                for rec in r.get("recommendations", [])
                if rec["priority"] == "high"
            ],
        }

    else:  # full_analysis
        base["best_matches"] = [
            {
                "title":             r.get("job_title"),
                "job_id":            r.get("job_id", ""),
                "gap_score":         r.get("gap_score"),
                "is_eligible":       r.get("is_eligible"),
                "eligibility_label": r.get("eligibility_label"),
                "skill_match_pct":   r.get("skill_match_pct"),
                "missing_mandatory": r.get("missing_mandatory"),
                "missing_certs":     r.get("missing_certs"),
                "present_skills":    r.get("present_skills"),
                "salary":            r.get("salary", ""),
                "location":          r.get("location", ""),
                "minimum_experience": r.get("minimum_experience"),
                "experience_years":  r.get("experience_years"),
                "recommendations":   r.get("recommendations", []),
                "summary":           r.get("summary"),
            }
            for r in top5
        ]

    return base
