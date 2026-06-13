# agents/hr_tools.py

import json
import re
from agents.groq_client import groq_chat
from dotenv import load_dotenv
from skill_gap.advanced_gap_analyzer import analyze_gap
from database.hr_repository import (
    save_hr_job, get_hr_job, get_all_hr_jobs,
    publish_hr_job, close_hr_job,
    save_interview_log, get_interview_logs,
    get_candidates_for_ranking,
)

load_dotenv()


# ── Tool 1: Generate JD ────────────────────────────────────────────────────────

def tool_generate_jd(role: str, location: str, experience_years: int, extra_context: str = "") -> dict:
    """LLM generates a complete Job Description for a maritime role."""
    prompt = f"""You are an expert maritime HR professional.
Generate a complete Job Description for this role. Return ONLY valid JSON:

{{
  "title": "job title",
  "role": "{role}",
  "location": "{location}",
  "salary": "estimated salary range in INR",
  "vacancies": 1,
  "minimum_experience": {experience_years},
  "summary": "2-3 line job summary",
  "mandatory_skills": ["skill1", "skill2", ...],
  "optional_skills": ["skill1", ...],
  "required_certifications": ["cert1", ...],
  "responsibilities": ["resp1", "resp2", ...],
  "benefits": ["benefit1", ...],
  "department": "maritime department name"
}}

Role: {role}
Location: {location}
Min Experience: {experience_years} years
Additional context: {extra_context or "Standard maritime role"}

Return ONLY the JSON object."""

    raw   = groq_chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            jd = json.loads(match.group(0))
            jd["status"] = "draft"
            return jd
        except Exception:
            pass
    return {"error": "Failed to generate JD", "raw": raw}


# ── Tool 2: Rank candidates for a job ─────────────────────────────────────────

def tool_rank_candidates(job: dict) -> list[dict]:
    """
    Fetch only candidates who applied for this job, run gap analysis,
    rank by gap_score descending.
    """
    from database.mongodb import applications_collection
    from database.candidate_repository import get_candidate

    job_id = str(job.get("_id", ""))

    # Get all applications for this job
    applications = list(applications_collection.find({"job_id": job_id}))
    if not applications:
        return []

    ranked = []
    for app in applications:
        try:
            c = get_candidate(app["candidate_id"])
            if not c:
                continue

            gap = analyze_gap(c, job)
            experience = c.get("experience", [])
            current_role = ""
            if experience:
                first_exp = experience[0] if isinstance(experience, list) else {}
                if isinstance(first_exp, dict):
                    current_role = first_exp.get("title") or first_exp.get("position") or str(first_exp)[:40]
                else:
                    current_role = str(first_exp)[:40]

            ranked.append({
                "candidate_id":      str(c.get("_id", "")),
                "name":              c.get("personal_info", {}).get("name", "Unknown")
                                     if isinstance(c.get("personal_info"), dict) else "Unknown",
                "current_role":      current_role,
                "applied_at":        app.get("applied_at", ""),
                "gap_score":         gap["gap_score"],
                "skill_match_pct":   gap["skill_match_pct"],
                "is_eligible":       gap["is_eligible"],
                "eligibility_label": gap["eligibility_label"],
                "missing_mandatory": gap["missing_mandatory"],
                "missing_certs":     gap["missing_certs"],
                "experience_years":  gap["experience_years"],
                "present_skills":    gap["present_skills"],
                "summary":           gap["summary"],
            })
        except Exception as e:
            ranked.append({
                "candidate_id": app.get("candidate_id", ""),
                "name": app.get("candidate_name", "?"),
                "current_role": "",
                "error": str(e),
                "gap_score": 0, "is_eligible": False,
            })

    return sorted(ranked, key=lambda x: x.get("gap_score", 0), reverse=True)


# ── Tool 3: Shortlist top N candidates ────────────────────────────────────────

def tool_shortlist_candidates(ranked: list[dict], top_n: int = 5) -> list[dict]:
    """Return top N unique candidates. Eligible first, then by gap_score."""
    seen_ids   = set()
    seen_names = set()
    unique     = []
    for c in ranked:
        cid   = c.get("candidate_id", "")
        cname = c.get("name", "").strip().lower()
        # Deduplicate by ID first, then by name as fallback
        if cid and cid in seen_ids:
            continue
        if cname and cname in seen_names:
            continue
        if cid:
            seen_ids.add(cid)
        if cname:
            seen_names.add(cname)
        unique.append(dict(c))

    eligible   = [c for c in unique if c.get("is_eligible")]
    ineligible = [c for c in unique if not c.get("is_eligible")]
    shortlisted = (eligible + ineligible)[:top_n]
    for i, c in enumerate(shortlisted):
        c["rank"] = i + 1
    return shortlisted


# ── Tool 4: Skill gap analysis for a candidate against a job ──────────────────

def tool_candidate_skill_gap(candidate_id: str, job_id: str) -> dict:
    """Detailed skill gap for one candidate vs one job."""
    from database.candidate_repository import get_candidate
    candidate = get_candidate(candidate_id)
    if not candidate:
        return {"error": f"Candidate {candidate_id} not found"}

    job = get_hr_job(job_id)
    if not job:
        return {"error": f"Job {job_id} not found"}

    gap = analyze_gap(candidate, job)
    gap["candidate_name"] = candidate.get("personal_info", {}).get("name", "?") \
                            if isinstance(candidate.get("personal_info"), dict) else "?"
    gap["job_title"] = job.get("title", "?")
    return gap


# ── Tool 5: Generate recruitment report ───────────────────────────────────────

def tool_generate_recruitment_report(job: dict, ranked: list[dict]) -> dict:
    """LLM generates a structured recruitment report."""
    top5_text = "\n".join(
        f"  {i+1}. {c['name']} — score={c.get('gap_score',0)}, "
        f"eligible={c.get('is_eligible')}, "
        f"missing={c.get('missing_mandatory',[])}"
        for i, c in enumerate(ranked[:5])
    )

    prompt = f"""You are a maritime HR analyst. Generate a recruitment report.
Return ONLY valid JSON:
{{
  "report_title": "...",
  "job_title": "...",
  "total_applicants": {len(ranked)},
  "eligible_count": {sum(1 for c in ranked if c.get('is_eligible'))},
  "shortlisted_count": {min(5, len(ranked))},
  "executive_summary": "3-4 sentence summary",
  "top_candidates_analysis": "analysis of top candidates",
  "common_skill_gaps": ["gap1", "gap2"],
  "hiring_recommendation": "clear recommendation",
  "next_steps": ["step1", "step2", "step3"]
}}

Job: {job.get('title')} at {job.get('location')}
Required skills: {job.get('mandatory_skills',[])}
Top candidates:
{top5_text}

Return ONLY JSON."""

    raw   = groq_chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {"error": "Failed to generate report", "raw": raw}


# ── Tool 6: Generate interview summary ────────────────────────────────────────

def tool_generate_interview_summary(
    candidate_name: str,
    job_title: str,
    notes: str,
    rating: int = 3,
) -> dict:
    """LLM generates structured interview summary from raw notes."""
    prompt = f"""You are a maritime HR interviewer. Generate an interview summary.
Return ONLY valid JSON:
{{
  "candidate_name": "{candidate_name}",
  "job_title": "{job_title}",
  "interview_rating": {rating},
  "overall_impression": "one sentence",
  "strengths": ["strength1", "strength2"],
  "concerns": ["concern1"],
  "technical_assessment": "paragraph",
  "cultural_fit": "paragraph",
  "recommendation": "hire|hold|reject",
  "recommendation_reason": "reason"
}}

Candidate: {candidate_name}
Role: {job_title}
Rating: {rating}/5
Interview notes:
{notes}

Return ONLY JSON."""

    raw   = groq_chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {"error": "Failed to generate summary", "raw": raw}


# ── Tool 7: Publish / close job ───────────────────────────────────────────────

def tool_publish_job(job_id: str) -> dict:
    ok = publish_hr_job(job_id)
    return {"success": ok, "job_id": job_id, "status": "published" if ok else "error"}


def tool_close_job(job_id: str) -> dict:
    ok = close_hr_job(job_id)
    return {"success": ok, "job_id": job_id, "status": "closed" if ok else "error"}


# ── Tool 8: Save HR job ────────────────────────────────────────────────────────

def tool_save_hr_job(jd: dict) -> dict:
    job_id = save_hr_job(jd)
    return {"job_id": job_id, "title": jd.get("title"), "status": "draft"}
