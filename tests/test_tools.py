from src.tools.ticket_tools import (
    MOCK_TICKET_DB,
    get_user_ticket_history,
    query_knowledge_base,
    update_ticket_status,
)


def test_knowledge_base_retrieval():
    res = query_knowledge_base("How do I request production database access?")
    assert "SOP-401" in res
    assert "Engineering Director" in res


def test_update_ticket_status_success():
    res = update_ticket_status("TCK-101", "critical", "Escalated due to executive visibility")
    assert res["success"] is True
    assert res["updated_priority"] == "critical"
    assert MOCK_TICKET_DB["TCK-101"]["priority"] == "critical"


def test_update_ticket_status_not_found():
    res = update_ticket_status("TCK-9999", "low", "Invalid ticket test")
    assert res["success"] is False
    assert "not found" in res["error"]


def test_get_user_history():
    history = get_user_ticket_history("U-552")
    assert len(history) == 2
    assert "VPN setup" in history[0]
