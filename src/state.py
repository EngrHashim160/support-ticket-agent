from typing import TypedDict, List, Literal, Optional, Dict

Category = Literal["Billing", "Technical", "Security", "General"]

class TicketState(TypedDict, total=False):
    subject: str    # Ticket title
    description: str # Description of the ticket
    category: Optional[Category] # Classification result
    context: List[str] # RAG Snippets
    draft: Optional[str] # Draft reply to the user
    review: Optional[Dict[str, str]]  # {"feedback": str} - reviewer comments
    approved: bool # Decision gate from REview node
    attempts: int # Number of tries
    failures: List[Dict[str, str]] # History snapshot for audit (optional)
