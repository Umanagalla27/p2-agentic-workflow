from src.graph import build_helpdesk_graph
from src.state import TicketInput


def test_helpdesk_graph_execution():
    app = build_helpdesk_graph()

    test_ticket = TicketInput(
        ticket_id="TCK-999",
        user_id="U-12",
        user_email="analyst@firm.com",
        subject="VPN connection dropping",
        description="My VPN keeps disconnecting every 5 minutes.",
    )

    state = {
        "ticket": test_ticket,
        "triage": None,
        "research": None,
        "pending_actions": [],
        "review_status": "pending",
        "resolution_notes": None,
        "iteration_count": 0,
        "security_flagged": False,
    }

    output = app.invoke(state, config={"configurable": {"thread_id": "test-thread-1"}})

    assert output["triage"] is not None
    assert output["triage"].category == "software"
    assert len(output["pending_actions"]) == 1
