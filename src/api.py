import sys
from pathlib import Path

# Add project root to sys.path to support direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from langgraph.types import Command
from pydantic import BaseModel, Field

from src.graph import build_secure_agent_graph
from src.state import TicketInput

app = FastAPI(
    title="P2 Enterprise Multi-Agent API",
    description="Multi-Agent Helpdesk with LangGraph, MCP, HITL Approvals, and Security Guardrails",
    version="1.0.0",
)

# Global compiled graph
agent_app = build_secure_agent_graph()


class TicketSubmitRequest(BaseModel):
    ticket_id: str
    user_id: str
    user_email: str
    subject: str
    description: str


class ApprovalDecisionRequest(BaseModel):
    thread_id: str
    approved: bool
    reviewer: str = Field(default="SecOps_Admin")
    reason: str = Field(default="Approved by policy")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "p2-multi-agent-system"}


@app.post("/v1/tickets/submit")
def submit_ticket(payload: TicketSubmitRequest):
    ticket = TicketInput(
        ticket_id=payload.ticket_id,
        user_id=payload.user_id,
        user_email=payload.user_email,
        subject=payload.subject,
        description=payload.description,
    )

    state = {
        "ticket": ticket,
        "triage": None,
        "research": None,
        "pending_actions": [],
        "review_status": "pending",
        "resolution_notes": None,
        "iteration_count": 0,
        "security_flagged": False,
    }

    thread_id = f"thread-{payload.ticket_id}"
    config = {"configurable": {"thread_id": thread_id}}

    # Stream execution until completion or HITL interrupt
    for _ in agent_app.stream(state, config=config):
        pass

    snapshot = agent_app.get_state(config)

    # Check if halted by HITL interrupt
    if snapshot.next and "action_planning_node" in snapshot.next:
        interrupt_info = (
            snapshot.tasks[0].interrupts[0].value
            if snapshot.tasks and snapshot.tasks[0].interrupts
            else {}
        )
        return {
            "ticket_id": payload.ticket_id,
            "thread_id": thread_id,
            "status": "waiting_for_human_approval",
            "approval_prompt": interrupt_info.get("question"),
            "proposed_action": interrupt_info.get("proposed_action"),
        }

    # Completed or Quarantined
    vals = snapshot.values
    return {
        "ticket_id": payload.ticket_id,
        "thread_id": thread_id,
        "status": vals.get("review_status"),
        "security_flagged": vals.get("security_flagged"),
        "resolution_notes": vals.get("resolution_notes"),
    }


@app.post("/v1/tickets/review")
def review_ticket(payload: ApprovalDecisionRequest):
    config = {"configurable": {"thread_id": payload.thread_id}}
    snapshot = agent_app.get_state(config)

    if not snapshot.next:
        raise HTTPException(
            status_code=400,
            detail=f"Thread {payload.thread_id} is not paused waiting for approval.",
        )

    # Resume graph execution with human decision
    decision_payload = {
        "approved": payload.approved,
        "reviewer": payload.reviewer,
        "reason": payload.reason,
    }

    for _ in agent_app.stream(Command(resume=decision_payload), config=config):
        pass

    final_snapshot = agent_app.get_state(config)
    final_vals = final_snapshot.values

    return {
        "thread_id": payload.thread_id,
        "status": final_vals.get("review_status"),
        "actions_taken": [a.dict() for a in final_vals.get("pending_actions", [])],
        "resolution_notes": final_vals.get("resolution_notes"),
    }
