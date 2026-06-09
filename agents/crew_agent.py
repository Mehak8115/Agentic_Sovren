# agents/crew_agent.py
"""
CrewAgent — deterministic pipeline + LLM for intent/response/questions.
"""

import json
import re

from agents.groq_client import groq_chat
from agents.crew_tools import (
    tool_parse_resume,
    tool_parse_resume_from_text,
    tool_extract_skills,
    tool_search_jobs,
    tool_certification_check,
    tool_crew_gap_analysis,
    tool_rank_jobs,
    tool_generate_recommendations,
    tool_build_response,
)

_VALID_INTENTS = ["suggest_jobs", "skill_gap", "career_plan", "full_analysis"]


class CrewAgent:

    def run(
        self,
        query: str,
        candidate_id: str | None = None,
        resume_text: str | None = None,
        save_candidate: bool = False,
        include_thought_process: bool = False,
    ) -> dict:
        self.memory: list[str] = []

        # Step 1: Classify intent
        intent = self._classify_intent(query)
        self._log(f"[INTENT] {intent} | query: '{query[:80]}'")

        # Step 2: Load candidate
        candidate = None
        if candidate_id:
            self._log(f"[TOOL] parse_resume(candidate_id={candidate_id})")
            candidate = tool_parse_resume(candidate_id)
            if not candidate:
                return self._error(f"Candidate not found: {candidate_id}", include_thought_process)
        elif resume_text:
            self._log("[TOOL] parse_resume_from_text()")
            candidate = tool_parse_resume_from_text(resume_text=resume_text, save=save_candidate)
            if not candidate:
                return self._error("Failed to parse resume", include_thought_process)
        else:
            return self._error("Provide candidate_id or resume_text", include_thought_process)

        self._log(f"[OBS]  Candidate: {self._name(candidate)}")

        # Step 3: Normalise skills
        self._log("[TOOL] extract_skills()")
        skill_profile = tool_extract_skills(candidate)
        candidate["skills"]         = skill_profile["skills"]
        candidate["certifications"] = skill_profile["certifications"]
        self._log(f"[OBS]  {len(skill_profile['skills'])} skills | {len(skill_profile['certifications'])} certs | {skill_profile['experience_years']} yrs")

        # Step 4: Fetch jobs
        self._log("[TOOL] search_jobs()")
        jobs = tool_search_jobs()
        if not jobs:
            return self._error("No available jobs found", include_thought_process)
        self._log(f"[OBS]  {len(jobs)} jobs found")

        # Step 5: Gap analysis per job
        gap_results: list[dict] = []
        for job in jobs:
            title = job.get("title", "?")
            cert  = tool_certification_check(candidate, job)
            self._log(f"[TOOL] cert_check → {title}: score={cert['cert_score']}%")
            gap = tool_crew_gap_analysis(candidate, job)
            self._log(f"[TOOL] gap_analysis → {title}: gap={gap['gap_score']} eligible={gap['is_eligible']}")
            gap_results.append(gap)

        # Step 6: Rank
        self._log("[TOOL] rank_jobs()")
        ranked = tool_rank_jobs(gap_results)
        if ranked:
            self._log(f"[OBS]  Top: {ranked[0].get('job_title')} (score {ranked[0].get('gap_score')})")

        # Step 7: Recommendations
        self._log("[TOOL] generate_recommendations()")
        ranked = tool_generate_recommendations(ranked)

        # Step 8: Build structured payload
        self._log(f"[TOOL] build_response(intent={intent})")
        structured = tool_build_response(candidate=candidate, ranked_results=ranked, intent=intent)

        # Step 9: LLM response + questions
        self._log("[LLM]  Generating response")
        nl_response, suggested_questions = self._generate_response(query, intent, structured)
        self._log("[DONE]")

        output = {
            "agent":               "Maritime Crew Agent",
            "intent":              intent,
            "candidate_name":      self._name(candidate),
            "candidate_id":        str(candidate.get("_id", "")) if candidate.get("_id") else "",
            "query":               query,
            "response":            nl_response,
            "suggested_questions": suggested_questions,
            "data":                structured,
        }
        if include_thought_process:
            output["thought_process"] = self.memory
        return output

    def _classify_intent(self, query: str) -> str:
        raw = groq_chat(
            messages=[{"role": "user", "content":
                "Classify into one label: suggest_jobs | skill_gap | career_plan | full_analysis\n"
                f'Query: "{query}"\nReply ONLY the label.'}],
            temperature=0,
        )
        raw = raw.lower()
        for i in _VALID_INTENTS:
            if i in raw:
                return i
        return "full_analysis"

    def _generate_response(self, query: str, intent: str, data: dict) -> tuple[str, list]:
        name          = data.get("candidate_name", "the candidate")
        total_jobs    = data.get("total_jobs", 0)
        eligible_jobs = data.get("eligible_jobs", 0)

        if intent == "suggest_jobs":
            matches = data.get("best_matches", [])
            items = "\n".join(
                f"  • {m['title']}: score={m['gap_score']}/100, eligible={m['is_eligible']}, "
                f"{m['eligibility_label']}, skill_match={m['skill_match_pct']}%"
                for m in matches
            )
            context_block = (
                f"Candidate: {name}\nJobs analysed: {total_jobs} | Eligible: {eligible_jobs}\n\nTop matches:\n{items}"
            )
        elif intent == "skill_gap":
            report = data.get("skill_gap_report", [])
            items = "\n".join(
                f"  • {r['title']}: skill_match={r['skill_match_pct']}%, "
                f"missing={r['missing_mandatory']}, missing_certs={r['missing_certs']}"
                for r in report
            )
            context_block = f"Candidate: {name}\n\nSkill gap:\n{items}"
        elif intent == "career_plan":
            plan = data.get("career_improvement_plan", {})
            opps = "\n".join(
                f"  • {o['title']}: score={o['gap_score']}, eligible={o['is_eligible']}"
                for o in plan.get("top_opportunities", [])
            )
            context_block = (
                f"Candidate: {name}\nOpportunities:\n{opps}\n"
                f"Skills to learn: {plan.get('priority_skills_to_learn', [])}\n"
                f"Certs to get: {plan.get('priority_certs_to_obtain', [])}"
            )
        else:
            matches = data.get("best_matches", [])
            items = "\n".join(
                f"  • {m.get('job_title')}: score={m.get('gap_score')}, eligible={m.get('is_eligible')}, "
                f"missing={m.get('missing_mandatory')}"
                for m in matches[:5]
            )
            context_block = f"Candidate: {name}\nJobs: {total_jobs} total, {eligible_jobs} eligible\n\nTop 5:\n{items}"

        prompt = f"""You are a helpful maritime career assistant.
User asked: "{query}"
Intent: {intent}

Candidate: **{name}**
Jobs analysed: {total_jobs} | Eligible: **{eligible_jobs}**

Data:
{context_block}

IMPORTANT FORMATTING RULES:
- Write in plain, friendly English — NO raw data like "eligible=True" or "score=80.0/100"
- Say "excellent match" not "score=80"
- Say "you are eligible" not "eligible=True"
- Say "you match 100% of required skills" not "skill_match=100.0%"
- Use **bold** for job titles, skills, certifications
- Use ## for section headers
- Use bullet points (- item) for lists
- Use ₹ for all salary mentions

Write a well-formatted maritime career response:
1. Brief **summary** of the candidate's situation
2. ## Top Job Matches — for each job: name, whether eligible, how good the match is, what's missing (in plain English)
3. ## Skills to Develop — what to learn and why
4. ## Recommendation — clear actionable advice

Then write ---QUESTIONS--- on its own line, and below it EXACTLY 5 maritime career follow-up questions as JSON array.
Questions should be specific to the candidate's actual results — certifications, training, salary, career path."""

        raw = groq_chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        if "---QUESTIONS---" in raw:
            parts = raw.split("---QUESTIONS---", 1)
            nl    = parts[0].strip()
            q_raw = parts[1].strip()
        else:
            nl    = raw
            q_raw = "[]"

        questions = []
        # Use greedy match to capture full JSON array
        m = re.search(r"\[.*\]", q_raw, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                questions = [q for q in parsed if isinstance(q, str)]
            except Exception:
                pass
        # Fallback if no questions parsed
        if not questions:
            questions = [
                f"What certifications do I need for the top matching roles?",
                f"How can I improve my skill match percentage?",
                f"What is the salary range for these positions?",
                f"What training courses would help me qualify for captain roles?",
                f"How long does it take to progress to senior maritime positions?",
            ]
        return nl, questions[:5]

    def _name(self, candidate: dict) -> str:
        info = candidate.get("personal_info", {})
        return info.get("name", "Unknown") if isinstance(info, dict) else "Unknown"

    def _error(self, msg: str, include_thought_process: bool) -> dict:
        out = {"error": msg, "suggested_questions": []}
        if include_thought_process:
            out["thought_process"] = self.memory
        return out

    def _log(self, msg: str):
        self.memory.append(msg)
