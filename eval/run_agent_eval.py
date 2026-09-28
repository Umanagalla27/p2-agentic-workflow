import json
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path to support direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.types import Command
from src.graph import build_secure_agent_graph
from src.state import TicketInput


def evaluate_agent_benchmark():
    with open("eval/scenarios.json", "r") as f:
        scenarios = json.load(f)

    app = build_secure_agent_graph()

    total = len(scenarios)
    correct_triage = 0
    correct_hitl_escalations = 0
    adversarial_blocked = 0
    total_adversarial = 0
    task_success_count = 0

    print(f"\n[Agent Eval] Starting automated benchmark on {total} enterprise scenarios...")
    start_time = time.perf_counter()

    for item in scenarios:
        ticket = TicketInput(
            ticket_id=item["id"],
            user_id="U-TEST",
            user_email="test@enterprise.com",
            subject="Automated Evaluation Case",
            description=item["description"],
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

        config = {"configurable": {"thread_id": f"eval-{item['id']}"}}

        # Stream execution
        for _ in app.stream(state, config=config):
            pass

        snapshot = app.get_state(config)

        # 1. Adversarial Injection Check
        if item["is_adversarial"]:
            total_adversarial += 1
            if snapshot.values.get("security_flagged") is True:
                adversarial_blocked += 1
                task_success_count += 1
            continue

        # 2. Triage Category Accuracy Check
        triage = snapshot.values.get("triage")
        if triage and triage.category == item["expected_category"]:
            correct_triage += 1

        # 3. HITL Trigger Accuracy Check
        was_paused = len(snapshot.next) > 0 and "action_planning_node" in snapshot.next[0]
        if item["requires_approval"] == was_paused:
            correct_hitl_escalations += 1

        # If paused for approval, simulate human approval and resume
        if was_paused:
            for _ in app.stream(Command(resume={"approved": True, "reviewer": "CI_Bot"}), config=config):
                pass
            snapshot = app.get_state(config)

        # 4. Overall Task Completion Check
        if snapshot.values.get("review_status") == "resolved":
            task_success_count += 1

    total_duration = time.perf_counter() - start_time
    standard_total = total - total_adversarial

    triage_acc = (correct_triage / standard_total) * 100
    hitl_acc = (correct_hitl_escalations / standard_total) * 100
    injection_block_rate = (adversarial_blocked / total_adversarial) * 100
    task_success_rate = (task_success_count / total) * 100

    print("\n" + "=" * 80)
    print("MULTI-AGENT ENTERPRISE BENCHMARK RESULTS (50 SCENARIOS)")
    print("=" * 80)
    print(f"Total Scenarios Evaluated:         {total}")
    print(f"Total Benchmark Runtime:           {total_duration:.2f} seconds ({total/total_duration:.1f} runs/sec)")
    print("-" * 80)
    print(f"Triage Categorization Accuracy:    {triage_acc:.1f}%")
    print(f"HITL Approval Trigger Accuracy:    {hitl_acc:.1f}%")
    print(f"Prompt Injection Block Rate:       {injection_block_rate:.1f}% (Adversarial Robustness)")
    print(f"End-to-End Task Success Rate:      {task_success_rate:.1f}%")
    print("=" * 80)

    # Save to results/
    os.makedirs("results", exist_ok=True)
    report = {
        "total_scenarios": total,
        "triage_accuracy": triage_acc,
        "hitl_trigger_accuracy": hitl_acc,
        "injection_block_rate": injection_block_rate,
        "task_success_rate": task_success_rate,
        "duration_seconds": round(total_duration, 2),
    }
    with open("results/agent_benchmark_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved evaluation report to results/agent_benchmark_report.json")


if __name__ == "__main__":
    evaluate_agent_benchmark()
