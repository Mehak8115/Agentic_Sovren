from pydantic import BaseModel


class AgentRequest(BaseModel):

    task: str

    candidate_id: str