from src.graph import build_graph

if __name__ == "__main__":
    graph = build_graph()
    initial_state = {
        "subject": "Password reset not working on mobile",
        "description": "User cannot reset password on iOS app.",
        "attempts": 0,
        "approved": False,
    }
    result = graph.invoke(initial_state)
    print("\nFinal state:\n", result)
