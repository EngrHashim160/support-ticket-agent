from typing import Dict

# Minimal placeholder: rule-based category classifier.
# Later we’ll replace with an LLM call.

def classify(state: Dict) -> Dict:
    text = (state.get("subject", "") + " " + state.get("description", "")).lower()
    if any(k in text for k in ["password", "login", "app", "ios", "android", "bug", "error", "api"]):
        category = "Technical"
    elif any(k in text for k in ["invoice", "billing", "charge", "refund", "payment"]):
        category = "Billing"
    elif any(k in text for k in ["security", "breach", "2fa", "mfa", "phish", "gdpr"]):
        category = "Security"
    else:
        category = "General"
    return {"category": category}
