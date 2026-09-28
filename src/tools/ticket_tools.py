from typing import Any

from pydantic import BaseModel, Field

# In-memory mock database for the helpdesk system
MOCK_TICKET_DB: dict[str, dict[str, Any]] = {
    "TCK-101": {
        "user_id": "U-552",
        "category": "access_control",
        "status": "open",
        "priority": "high",
        "notes": [],
    }
}

MOCK_USER_HISTORY: dict[str, list[str]] = {
    "U-552": ["TCK-089: VPN setup (Resolved)", "TCK-094: Password reset (Resolved)"]
}


class KnowledgeQueryInput(BaseModel):
    query: str = Field(description="Search query to lookup internal IT policies and SOPs.")


class TicketUpdateInput(BaseModel):
    ticket_id: str = Field(description="Unique ID of the ticket, e.g. TCK-101.")
    new_priority: str = Field(
        description="New priority level: 'low', 'medium', 'high', 'critical'."
    )
    note: str = Field(description="Reason for the update.")


def query_knowledge_base(query: str) -> str:
    """Simulates querying P1's RAG system for internal compliance and IT procedures."""
    lowered = query.lower()
    if "access" in lowered or "database" in lowered:
        return (
            "[Policy SOP-401] Access Control: Production database read access requires "
            "written authorization from an Engineering Director and Multi-Factor "
            "Authentication (MFA) validation."
        )
    if "hardware" in lowered or "laptop" in lowered:
        return (
            "[Policy SOP-202] Hardware: Equipment failures must be reported within 24 hours. "
            "Temporary loaner laptops can be issued by IT Support on Floor 3."
        )
    return (
        "[Policy SOP-100] General IT: For unresolved issues, escalate to "
        "Tier-2 engineering support."
    )


def update_ticket_status(ticket_id: str, new_priority: str, note: str) -> dict[str, Any]:
    """Updates ticket priority and appends audit notes in the database."""
    if ticket_id not in MOCK_TICKET_DB:
        return {"success": False, "error": f"Ticket {ticket_id} not found."}

    MOCK_TICKET_DB[ticket_id]["priority"] = new_priority
    MOCK_TICKET_DB[ticket_id]["notes"].append(note)
    return {
        "success": True,
        "ticket_id": ticket_id,
        "updated_priority": new_priority,
        "notes_count": len(MOCK_TICKET_DB[ticket_id]["notes"]),
    }


def get_user_ticket_history(user_id: str) -> list[str]:
    """Fetches historical support tickets for a user to provide context."""
    return MOCK_USER_HISTORY.get(user_id, ["No prior ticket history found."])
