import sys
from pathlib import Path

# Add project root to sys.path to support direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from src.security.guardrails import EnterpriseGuardrails
from src.state import (
    ActionExecution,
    AgentWorkflowState,
    ResearchFinding,
    TriageAssessment,
)
from src.tools.ticket_tools import query_knowledge_base, update_ticket_status

# --- Security Ingestion Node ---


def security_guardrail_node(state: AgentWorkflowState) -> dict:
    """Security Guardrail: Redacts PII and quarantines prompt injection attempts."""
    raw_desc = state["ticket"].description
    scan = EnterpriseGuardrails.scan_input(raw_desc)

    if not scan.is_safe:
        print(f"\n[SECURITY ALERT] Malicious payload detected: {scan.detected_threats}")
        return {
            "security_flagged": True,
            "review_status": "escalated",
            "resolution_notes": (
                f"QUARANTINED: Prompt injection detected ({scan.detected_threats[0]})"
            ),
        }

    # Update ticket description with sanitized (PII-redacted) text
    sanitized_ticket = state["ticket"].copy(update={"description": scan.sanitized_text})
    return {
        "ticket": sanitized_ticket,
        "security_flagged": False,
    }


def quarantine_node(state: AgentWorkflowState) -> dict:
    """Terminal node for quarantined malicious inputs."""
    print("[SECURITY] Ticket routed to quarantine. All downstream tool execution terminated.")
    return {"review_status": "escalated"}


def check_security_status(state: AgentWorkflowState) -> str:
    """Conditional Edge: Routes malicious tickets directly to quarantine."""
    if state.get("security_flagged", False):
        return "quarantine_node"
    return "triage_node"


# --- Core Agent Nodes (Triage, Research, Action, Execution) ---


def triage_node(state: AgentWorkflowState) -> dict:
    desc = state["ticket"].description.lower()

    if "access" in desc or "permission" in desc or "grant" in desc:
        category = "access_control"
        urgency = "high"
        requires_approval = True
    elif "breach" in desc or "leak" in desc or "security" in desc:
        category = "security"
        urgency = "critical"
        requires_approval = True
    else:
        category = "software"
        urgency = "medium"
        requires_approval = False

    triage = TriageAssessment(
        category=category,
        urgency=urgency,
        requires_human_approval=requires_approval,
        summary=f"Categorized as {category} with {urgency} urgency.",
    )
    return {"triage": triage, "iteration_count": state.get("iteration_count", 0) + 1}


def research_node(state: AgentWorkflowState) -> dict:
    category = state["triage"].category if state["triage"] else "general"
    policy_doc = query_knowledge_base(category)

    findings = [
        ResearchFinding(
            policy_reference="MCP-KB-Internal-SOP",
            suggested_action=policy_doc,
            confidence=0.95,
        )
    ]
    return {"research": findings}


def action_planning_node(state: AgentWorkflowState) -> dict:
    triage = state["triage"]
    ticket_id = state["ticket"].ticket_id

    # Enforce Least-Privilege Tool Check
    tool_to_use = "modify_ticket_priority"
    if not EnterpriseGuardrails.validate_tool_permission("action_agent", tool_to_use):
        raise PermissionError(f"Action agent unauthorized to invoke {tool_to_use}")

    proposed_action = ActionExecution(
        tool_name=tool_to_use,
        parameters={
            "ticket_id": ticket_id,
            "new_priority": triage.urgency,
            "note": f"System updated via agent based on triage: {triage.summary}",
        },
        status="pending" if triage.requires_human_approval else "approved",
    )

    if triage.requires_human_approval:
        print(f"\n[HITL] Pausing execution for human approval on Ticket {ticket_id}...")
        human_decision = interrupt(
            {
                "question": f"Authorize priority escalation to '{triage.urgency}' for {ticket_id}?",
                "proposed_action": proposed_action.dict(),
            }
        )

        if human_decision.get("approved") is True:
            proposed_action.status = "approved"
            proposed_action.result = f"Approved by human: {human_decision.get('reviewer', 'Admin')}"
        else:
            proposed_action.status = "rejected"
            proposed_action.result = f"Rejected by human: {human_decision.get('reason', 'Denied')}"

    return {"pending_actions": [proposed_action]}


def execution_node(state: AgentWorkflowState) -> dict:
    actions = state.get("pending_actions", [])
    if not actions:
        return {"review_status": "resolved"}

    latest_action = actions[-1]
    if latest_action.status == "approved":
        params = latest_action.parameters
        tool_result = update_ticket_status(
            ticket_id=params["ticket_id"],
            new_priority=params["new_priority"],
            note=params["note"],
        )
        latest_action.status = "executed"
        latest_action.result = str(tool_result)
        return {"review_status": "resolved", "resolution_notes": "Action executed successfully."}
    else:
        return {"review_status": "escalated", "resolution_notes": "Action was denied by reviewer."}


# --- Graph Construction ---


def build_secure_agent_graph():
    workflow = StateGraph(AgentWorkflowState)

    workflow.add_node("security_guardrail_node", security_guardrail_node)
    workflow.add_node("quarantine_node", quarantine_node)
    workflow.add_node("triage_node", triage_node)
    workflow.add_node("research_node", research_node)
    workflow.add_node("action_planning_node", action_planning_node)
    workflow.add_node("execution_node", execution_node)

    # Ingestion flow
    workflow.add_edge(START, "security_guardrail_node")
    workflow.add_conditional_edges(
        "security_guardrail_node",
        check_security_status,
        {"quarantine_node": "quarantine_node", "triage_node": "triage_node"},
    )
    workflow.add_edge("quarantine_node", END)
    workflow.add_edge("triage_node", "research_node")
    workflow.add_edge("research_node", "action_planning_node")
    workflow.add_edge("action_planning_node", "execution_node")
    workflow.add_edge("execution_node", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# Compatibility aliases
build_hitl_graph = build_secure_agent_graph
build_helpdesk_graph = build_secure_agent_graph
