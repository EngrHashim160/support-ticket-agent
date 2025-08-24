from typing import Dict

# Minimal reviewer: approves if draft includes at least one retrieved step.
# We'll later replace this with an LLM-based structured review.

def review(state: Dict) -> Dict:
    draft = state.get("draft", "")
    approved = "Context:\n-" in draft
    feedback = "Looks good." if approved else "Please include at least one concrete step from retrieval context."
    return {"approved": approved, "review": {"feedback": feedback}}
