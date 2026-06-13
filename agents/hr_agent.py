# agents/hr_agent.py
"""
HRAgent — deterministic pipeline + LLM for intent/response.
"""

import json
import re
from agents.groq_client import groq_chat
from dotenv import load_dotenv

from agents.hr_tools import (
    tool_generate_jd,
    tool_rank_candidates,
    tool_shortlist_candidates,
    tool_candidate_skill_gap,
    tool_generate_recruitment_report,
    tool_generate_interview_summary,
    tool_publish_job,
    tool_close_job,
    tool_save_hr_job,
)
from database.hr_repository import (
    get_hr_job,
    get_all_hr_jobs,
    save_interview_log,
)

load_dotenv()

_VALID_INTENTS = [
    "generate_jd", "rank_candidates", "skill_gap",
    "recruitment_report", "interview_summary",
    "publish_job", "close_job", "list_jobs",
]


class HRAgent:

    def run(self, query: str, **kwargs) -> dict:
        self.memory: list[str] = []
        include_thought = kwargs.get("include_thought_process", False)

        intent = self._classify_intent(query)
        self._log(f"[INTENT] {intent}")

        result = self._dispatch(intent, kwargs)

        if include_thought:
            result["thought_process"] = self.memory
        return result

    def _dispatch(self, intent: str, kw: dict) -> dict:
        if intent == "generate_jd":      return self._do_generate_jd(kw)
        if intent == "rank_candidates":  return self._do_rank_candidates(kw)
        if intent == "skill_gap":        return self._do_skill_gap(kw)
        if intent == "recruitment_report": return self._do_recruitment_report(kw)
        if intent == "interview_summary":  return self._do_interview_summary(kw)
        if intent == "publish_job":      return self._do_publish_job(kw)
        if intent == "close_job":        return self._do_close_job(kw)
        if intent == "list_jobs":        return self._do_list_jobs(kw)
        return {"error": f"Unknown intent: {intent}"}

    # ── Intent handlers ────────────────────────────────────────────────────────

    def _do_generate_jd(self, kw: dict) -> dict:
        role  = kw.get("role", "Deck Officer")
        loc   = kw.get("location", "Mumbai")
        exp   = int(kw.get("experience_years", 3))
        extra = kw.get("extra_context", "")
        self._log(f"[TOOL] generate_jd(role={role}, loc={loc}, exp={exp})")
        jd = tool_generate_jd(role, loc, exp, extra)
        if "error" in jd:
            return {"error": jd["error"]}
        self._log("[TOOL] save_hr_job()")
        saved = tool_save_hr_job(jd)
        self._log(f"[OBS]  job_id={saved['job_id']}")
        nl = self._nl("generate_jd", {"jd": jd, "job_id": saved["job_id"]})
        return {"agent": "Maritime HR Agent", "intent": "generate_jd",
                "response": nl, "data": {"jd": jd, "job_id": saved["job_id"]}}

    def _do_rank_candidates(self, kw: dict) -> dict:
        job_id = kw.get("job_id")
        if not job_id:
            return {"error": "job_id required"}

        # job_id from dropdown is available_jobs._id (since notifications store it that way)
        from database.mongodb import available_jobs_collection
        from bson import ObjectId

        # Try available_jobs first (applications link to this)
        avail_job = None
        try:
            avail_job = available_jobs_collection.find_one({"_id": ObjectId(job_id)})
        except Exception:
            pass

        if avail_job:
            job = dict(avail_job)
            job["_id"] = str(avail_job["_id"])
        else:
            # Fallback: try hr_jobs
            job = get_hr_job(job_id)
            if not job:
                return {"error": f"Job not found: {job_id}"}
            # Find available_jobs record for this hr_job
            avail = available_jobs_collection.find_one({"hr_job_id": job_id})
            if avail:
                job["_id"] = str(avail["_id"])
            else:
                job["_id"] = job_id

        self._log(f"[TOOL] rank_candidates(job={job.get('title')}) using _id={job['_id']}")
        ranked = tool_rank_candidates(job)
        if not ranked:
            return {
                "agent": "Maritime HR Agent",
                "intent": "rank_candidates",
                "response": f"No applications received yet for **{job.get('title')}**. Share the job posting with candidates first.",
                "data": {"job_title": job.get("title"), "total_ranked": 0, "eligible": 0, "shortlist": [], "all_ranked": []}
            }
        shortlist = tool_shortlist_candidates(ranked, top_n=5)
        nl = self._nl("rank_candidates", {"job": job, "shortlist": shortlist, "total": len(ranked),
                                           "eligible": sum(1 for c in ranked if c.get("is_eligible"))})
        return {"agent": "Maritime HR Agent", "intent": "rank_candidates", "response": nl,
                "data": {"job_title": job.get("title"), "total_ranked": len(ranked),
                         "eligible": sum(1 for c in ranked if c.get("is_eligible")),
                         "shortlist": shortlist, "all_ranked": ranked}}

    def _do_skill_gap(self, kw: dict) -> dict:
        cid = kw.get("candidate_id")
        jid = kw.get("job_id")
        if not cid or not jid:
            return {"error": "candidate_id and job_id required"}
        self._log(f"[TOOL] candidate_skill_gap({cid}, {jid})")
        gap = tool_candidate_skill_gap(cid, jid)
        if "error" in gap:
            return gap
        nl = self._nl("skill_gap", {"gap": gap})
        return {"agent": "Maritime HR Agent", "intent": "skill_gap", "response": nl, "data": gap}

    def _do_recruitment_report(self, kw: dict) -> dict:
        jid = kw.get("job_id")
        if not jid:
            return {"error": "job_id required"}
        job = get_hr_job(jid)
        if not job:
            return {"error": f"Job not found: {jid}"}
        self._log("[TOOL] rank_candidates()")
        ranked = tool_rank_candidates(job)
        self._log("[TOOL] generate_recruitment_report()")
        report = tool_generate_recruitment_report(job, ranked)
        nl = self._nl("recruitment_report", {"report": report})
        return {"agent": "Maritime HR Agent", "intent": "recruitment_report",
                "response": nl, "data": {"report": report, "ranked_candidates": ranked[:10]}}

    def _do_interview_summary(self, kw: dict) -> dict:
        notes = kw.get("interview_notes", "")
        if not notes:
            return {"error": "interview_notes required"}
        cname = kw.get("candidate_name", "Candidate")
        jtitle = kw.get("job_title", "Maritime Role")
        rating = int(kw.get("interview_rating", 3))
        jid    = kw.get("job_id", "")
        self._log("[TOOL] generate_interview_summary()")
        summary = tool_generate_interview_summary(cname, jtitle, notes, rating)
        if "error" in summary:
            return summary
        if jid:
            save_interview_log({**summary, "job_id": jid})
            self._log("[OBS]  Interview log saved")
        nl = self._nl("interview_summary", {"summary": summary})
        return {"agent": "Maritime HR Agent", "intent": "interview_summary",
                "response": nl, "data": summary}

    def _do_publish_job(self, kw: dict) -> dict:
        jid = kw.get("job_id")
        if not jid:
            return {"error": "job_id required"}
        self._log(f"[TOOL] publish_job({jid})")
        result = tool_publish_job(jid)
        short  = jid[:8] + "..."
        return {"agent": "Maritime HR Agent", "intent": "publish_job",
                "response": f"✅ Job **{short}** has been published successfully! It is now visible to crew members who can search and apply.",
                "data": result}

    def _do_close_job(self, kw: dict) -> dict:
        jid = kw.get("job_id")
        if not jid:
            return {"error": "job_id required"}
        self._log(f"[TOOL] close_job({jid})")
        result = tool_close_job(jid)
        return {"agent": "Maritime HR Agent", "intent": "close_job",
                "response": f"Job **{jid}** closed. No longer visible to crew.",
                "data": result}

    def _do_list_jobs(self, kw: dict) -> dict:
        status = kw.get("status")
        self._log(f"[TOOL] get_all_hr_jobs(status={status})")
        jobs = get_all_hr_jobs(status)
        nl = self._nl("list_jobs", {"jobs": jobs, "count": len(jobs)})
        return {"agent": "Maritime HR Agent", "intent": "list_jobs",
                "response": nl, "data": {"jobs": jobs, "count": len(jobs)}}

    # ── LLM helpers ───────────────────────────────────────────────────────────

    def _classify_intent(self, query: str) -> str:
        raw = groq_chat(
            messages=[{"role": "user", "content":
                f"Classify HR query into one: {', '.join(_VALID_INTENTS)}\n"
                f'Query: "{query}"\nReply ONLY the label.'}],
            temperature=0,
        ).lower()
        for i in _VALID_INTENTS:
            if i in raw:
                return i
        return "list_jobs"

    def _nl(self, intent: str, data: dict) -> str:
        context = json.dumps(data, default=str, indent=2)[:2000]
        return groq_chat(
            messages=[{"role": "user", "content":
                f"""You are a helpful maritime HR assistant. Intent: {intent}.
Data: {context}

Write a clear, plain-English response for the HR manager. Rules:
- Talk naturally, like a knowledgeable colleague
- No technical jargon, no raw values like "gap_score=80" or "is_eligible=True"
- Say "strong candidate" not "gap_score=80"
- Say "qualifies for the role" not "is_eligible=True"
- **Bold** names, job titles, key numbers
- Use ## headers and bullet points for structure
- Use ₹ for all salaries
- Be specific and actionable"""}],
            temperature=0.3,
        )

    def _log(self, msg: str):
        self.memory.append(msg)
