from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict

from src.state import TicketState
from src.nodes.classify import classify
from src.nodes.retrieve import retrieve
from src.nodes.draft import draft
from src.nodes.review import review
from src.nodes.refine import refine
from src.nodes.escalate import escalate


def _inc_attempt(state: TicketState) -> Dict:
    attempts = state.get("attempts", 0) + 1
    failures = state.get("failures", [])
    failures.append({
        "draft": state.get("draft", ""),
        "feedback": (state.get("review", {}) or {}).get("feedback", ""),
    })
    return {"attempts": attempts, "failures": failures}


def _branch_after_review(state: TicketState) -> str:
    return "END" if state.get("approved") else "RETRY"


def build_graph():
    g = StateGraph(TicketState)

    g.add_node("classify", classify)
    g.add_node("retrieve", retrieve)
    g.add_node("draft", draft)
    g.add_node("review", review)
    g.add_node("refine", refine)
    g.add_node("escalate", escalate)
    g.add_node("inc_attempt", _inc_attempt)

    g.set_entry_point("classify")
    g.add_edge("classify", "retrieve")
    g.add_edge("retrieve", "draft")
    g.add_edge("draft", "review")

    # If approved -> END; else increment attempts then either refine or escalate
    g.add_conditional_edges("review", _branch_after_review, {"END": END, "RETRY": "inc_attempt"})

    def _route_retry(state: TicketState) -> str:
        return "refine" if state.get("attempts", 0) < 2 else "escalate"

    g.add_conditional_edges("inc_attempt", _route_retry, {"refine": "refine", "escalate": "escalate"})

    # After refine, try the generate→review path again
    g.add_edge("refine", "retrieve")

    checkpointer = MemorySaver()
    return g.compile(checkpointer=checkpointer)
