from src import graph as graph_module

def test_one_retry_then_approve(monkeypatch):
    call_count = {"n": 0}

    def _review_once_then_pass(state: dict) -> dict:
        # First review: reject with feedback that should influence refine/retrieve.
        if call_count["n"] == 0:
            call_count["n"] += 1
            return {
                "approved": False,
                "review": {"feedback": "Mention mobile iOS steps and link to password policy."},
            }
        # Second review: approve
        return {"approved": True, "review": {"feedback": "Looks good now."}}

    # Patch the reviewer used by graph.py before building the graph
    monkeypatch.setattr(graph_module, "review", _review_once_then_pass, raising=True)

    g = graph_module.build_graph()
    config = {"configurable": {"thread_id": "pytest-retry"}}

    initial_state = {
        "subject": "Password reset not working on mobile",
        "description": "User cannot reset password on iOS app.",
        "attempts": 0,
        "approved": False,
    }

    final_state = g.invoke(initial_state, config=config)

    # It should have retried exactly once
    assert final_state.get("approved") is True
    assert final_state.get("attempts", 0) == 1
    # Optional: refine_hint should have been set during the failed pass
    assert "refine_hint" in final_state or final_state.get("attempts", 0) >= 1
