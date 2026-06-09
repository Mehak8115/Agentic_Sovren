# agents/supervisor_agent.py

from agents.crew_agent import CrewAgent


class SupervisorAgent:

    def __init__(self):
        self.crew_agent = CrewAgent()

    def run(
        self,
        query: str,
        candidate_id: str | None = None,
        resume_text: str | None = None,
        save_candidate: bool = False,
        include_thought_process: bool = False,
    ) -> dict:
        if not query or not str(query).strip():
            return {"error": "query is required"}

        if not candidate_id and not resume_text:
            return {"error": "Provide either candidate_id or resume_text (raw resume text)"}

        return self.crew_agent.run(
            query=str(query).strip(),
            candidate_id=str(candidate_id).strip() if candidate_id else None,
            resume_text=resume_text,
            save_candidate=save_candidate,
            include_thought_process=include_thought_process,
        )
