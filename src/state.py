from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class TicketInput(BaseModel):
    ticket_id: str
    user_id: str
    user_email: str
    subject: str
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TriageAssessment(BaseModel):
    category: Literal["hardware", "software", "access_control", "billing", "security"]
    urgency: Literal["low", "medium", "high", "critical"]
    requires_human_approval: bool
    summary: str


class ResearchFinding(BaseModel):
    policy_reference: str
    suggested_action: str
    confidence: float


class ActionExecution(BaseModel):
    tool_name: str
    parameters: dict[str, Any]
    status: Literal["pending", "approved", "rejected", "executed"]
    result: str | None = None


# Custom reducer to append actions to the audit log rather than overwriting
def append_action(
    existing: list[ActionExecution] | None, new: list[ActionExecution]
) -> list[ActionExecution]:
    if existing is None:
        return new
    return existing + new


class AgentWorkflowState(TypedDict):
    """
    The shared state across all agents in the LangGraph StateGraph.
    Every node reads from this and returns an updated slice.
    """

    ticket: TicketInput
    triage: TriageAssessment | None
    research: list[ResearchFinding] | None
    pending_actions: Annotated[list[ActionExecution], append_action]
    review_status: Literal["pending", "approved", "escalated", "resolved"]
    resolution_notes: str | None
    iteration_count: int
    security_flagged: bool
