import csv
from pathlib import Path
from typing import Dict

# Logs escalations to a CSV so humans can review failed cases.

def escalate(state: Dict) -> Dict:
    path = Path("escalation_log.csv")
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["subject", "description", "category", "attempts", "last_feedback"],
        )
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "subject": state.get("subject"),
                "description": state.get("description"),
                "category": state.get("category"),
                "attempts": state.get("attempts"),
                "last_feedback": (state.get("review", {}) or {}).get("feedback", ""),
            }
        )
    return {}