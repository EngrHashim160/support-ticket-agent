from src.graph import build_graph

if __name__ == "__main__":
    graph = build_graph()
    initial_state = {
        "subject": "Password reset not working on mobile",
        "description": "User cannot reset password on iOS app.",
        "attempts": 0,
        "approved": False,
    }
    # Provide a thread_id for the checkpointer
    config = {"configurable": {"thread_id": "local-demo"}}
    result = graph.invoke(initial_state, config=config)
    print("\nFinal state:\n", result)
