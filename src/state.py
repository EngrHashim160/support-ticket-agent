from typing import TypedDict, List, Literal, Optional, Dict

Category = Literal["Billing", "Technical", "Security", "General"]

class TicketState(TypedDict, total=False):
    subject: str
    description: str
    category: Optional[Category]
    context: List[str]
    draft: Optional[str]
    review: Optional[Dict[str, str]]  # {"feedback": str}
    approved: bool
    attempts: int
    failures: List[Dict[str, str]]
