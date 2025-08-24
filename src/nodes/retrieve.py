from typing import Dict, List

# Placeholder retrieval: returns fixed snippets so the pipeline is testable.
# Later we’ll swap this with FAISS-based category-aware retrieval.

def retrieve(state: Dict) -> Dict:
    cat = state.get("category", "General")
    demo_docs = {
        "Technical": [
            "Reset your password from Settings → Account → Reset Password.",
            "Ensure app version is latest; try clearing cache and retry.",
            "If email not received, check spam and rate limits.",
        ],
        "Billing": [
            "Invoices are sent on the 1st of each month.",
            "Refunds follow policy section 3.2 (no partial refunds after 14 days).",
        ],
        "Security": [
            "MFA required for admin roles; see Security Policy §4.",
            "Password rules: 12+ chars, mixed case, symbol.",
        ],
        "General": [
            "Thanks for contacting support; we’re here to help.",
        ],
    }
    docs: List[str] = demo_docs.get(cat, demo_docs["General"])[:3]
    return {"context": docs}
