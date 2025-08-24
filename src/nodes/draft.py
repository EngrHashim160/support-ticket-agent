from typing import Dict, List

def _format_context(ctx: List[str]) -> str:
    if not ctx:
        return ""
    return "\n\nContext:\n- " + "\n- ".join(ctx)

def draft(state: Dict) -> Dict:
    context = state.get("context", [])
    message = (
        "Hi there, thanks for reaching out.\n\n"
        "I understand you're facing an issue. Here are steps that often resolve it:"
        + _format_context(context)
        + "\n\nIf this doesn’t help, please reply with your OS/app version so we can dig deeper."
    )
    return {"draft": message}
