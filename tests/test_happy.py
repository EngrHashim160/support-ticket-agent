import types
from src import graph as graph_module

def test_happy_path(monkeypatch):
    # Monkeypatch the reviewer inside the graph module so the test is deterministic.
    def _approve_always(state: dict) -> dict:
        return {"approved": True, "review": {"feedback": "Looks good."}}

    monkeypatch.setattr(graph_module, "review", _approve_always, raising=True)

    config = {"configurable": {"thread_id": "pytest-happy"}}
    g = graph_module.build_graph()

    initial_state = {
        "subject": "Password reset not working on mobile",
        "description": "User cannot reset password on iOS app.",
        "attempts": 0,
        "approved": False,
    }

    final_state = g.invoke(initial_state, config=config)

    # Core expectations for the happy path
    assert final_state.get("category") in {"Technical", "Billing", "Security", "General"}
    assert isinstance(final_state.get("context"), list) and len(final_state["context"]) >= 1
    assert isinstance(final_state.get("draft"), str) and len(final_state["draft"]) > 0
    assert final_state.get("approved") is True
    assert final_state.get("attempts", 0) == 0
