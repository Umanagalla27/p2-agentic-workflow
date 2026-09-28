import sys
from pathlib import Path

# Add project root to sys.path to support direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.types import Command
from src.graph import build_hitl_graph
from src.state import TicketInput


def test_hitl_approval_flow():
    app = build_hitl_graph()

    thread_id = "ticket-session-42"
    config = {"configurable": {"thread_id": thread_id}}

    ticket = TicketInput(
        ticket_id="TCK-101",
        user_id="U-552",
        user_email="secops@firm.com",
        subject="Critical Database Access Needed",
        description="We suspect a security data breach, need immediate production read access.",
    )

    initial_state = {
        "ticket": ticket,
        "triage": None,
        "research": None,
        "pending_actions": [],
        "review_status": "pending",
        "resolution_notes": None,
        "iteration_count": 0,
        "security_flagged": False,
    }

    print("\n--- PHASE 1: STARTING GRAPH EXECUTION ---")
    # 1. Run until the interrupt is triggered
    for event in app.stream(initial_state, config=config):
        print(f"Node completed: {list(event.keys())}")

    # Inspect state at interrupt
    snapshot = app.get_state(config)
    print(f"\n[Graph State at Pause]: Next Node to run = {snapshot.next}")
    if snapshot.tasks and snapshot.tasks[0].interrupts:
        interrupt_info = snapshot.tasks[0].interrupts[0].value
        print(f"[Approval Prompt]: {interrupt_info['question']}")
        print(f"[Proposed Action]: {interrupt_info['proposed_action']['tool_name']}")

    print("\n--- PHASE 2: HUMAN PROVIDES APPROVAL ---")
    # 2. Resume graph with human decision using Command(resume=...)
    human_approval_payload = {
        "approved": True,
        "reviewer": "Alice (SecOps Director)",
    }

    for event in app.stream(Command(resume=human_approval_payload), config=config):
        print(f"Node completed: {list(event.keys())}")

    final_state = app.get_state(config).values
    print("\n" + "=" * 60)
    print("FINAL EXECUTION STATUS")
    print("=" * 60)
    print(f"Review Status:    {final_state['review_status']}")
    print(f"Action Status:    {final_state['pending_actions'][-1].status}")
    print(f"Execution Result: {final_state['pending_actions'][-1].result}")
    print(f"Resolution Notes: {final_state['resolution_notes']}")
    print("=" * 60)


if __name__ == "__main__":
    test_hitl_approval_flow()
