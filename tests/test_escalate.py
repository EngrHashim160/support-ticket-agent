import csv
from pathlib import Path
from src import graph as graph_module
import src.nodes.escalate as escalate_module

def test_escalation_after_two_failures(monkeypatch, tmp_path):
    # Force reviewer to always reject
    def _always_reject(state: dict) -> dict:
        return {
            "approved": False,
            "review": {"feedback": "Unfixable error for testing escalation."},
        }

    monkeypatch.setattr(graph_module, "review", _always_reject, raising=True)

    # Redirect escalation log path inside the escalate module
    log_file = tmp_path / "escalation_log.csv"
    monkeypatch.setattr(escalate_module, "Path", lambda p="escalation_log.csv": log_file, raising=True)

    g = graph_module.build_graph()
    config = {"configurable": {"thread_id": "pytest-escalate"}}

    initial_state = {
        "subject": "Refund not received",
        "description": "Customer says last month’s payment wasn’t refunded.",
        "attempts": 0,
        "approved": False,
    }

    final_state = g.invoke(initial_state, config=config)

    # It should end up not approved, with attempts == 2
    assert final_state.get("approved") is False
    assert final_state.get("attempts") == 2

    # Check that escalation log file was written with header + one row
    rows = list(csv.DictReader(log_file.open()))
    assert len(rows) == 1
    assert rows[0]["subject"] == "Refund not received"
    assert rows[0]["category"] in {"Billing", "Technical", "Security", "General"}
    assert rows[0]["attempts"] == "2"
