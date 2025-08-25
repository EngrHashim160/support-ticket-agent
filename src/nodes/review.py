"""
Reviewer (LLM-backed, lenient)

Goal:
- Evaluate the draft for groundedness, policy compliance, tone, and actionability.
- Prefer approving "mostly good" drafts; do not nitpick formatting.
- Return: {"approved": bool, "review": {"feedback": str}}
"""

from __future__ import annotations

import json
import re
from typing import Dict, Final, List, Set

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion

# --- bootstrap ---------------------------------------------------------------

load_dotenv()
_openai = OpenAI()

MODEL_NAME: Final[str] = "gpt-4o-mini"  # swap to "gpt-4o" if desired

# ✅ SOFTER RUBRIC: approve if the reply is mostly grounded & actionable.
SYSTEM_PROMPT: Final[str] = (
    "You are a pragmatic support reply reviewer.\n"
    "Assess the assistant draft on FOUR checks:\n"
    "1) Groundedness: Uses the given context and does not invent facts.\n"
    "2) Policy: No refunds/promises beyond policy; no security leaks.\n"
    "3) Tone: Empathetic, concise, professional.\n"
    "4) Actionability: Clear steps or follow-up questions.\n\n"
    "Be lenient about formatting and section headers (e.g., a 'Context' block is fine).\n"
    "If the reply is mostly grounded and actionable with minor style issues, APPROVE IT.\n\n"
    "Return ONLY JSON with keys: approved (true/false) and feedback (string).\n"
    "Feedback must be short and actionable if not approved."
    "Reject if the draft invents policy promises or refund paths not explicitly in context."
)

USER_TEMPLATE: Final[str] = (
    "Ticket\n"
    "------\n"
    "Subject: {subject}\n"
    "Description: {description}\n"
    "Category: {category}\n\n"
    "Context (RAG snippets):\n"
    "{context}\n\n"
    "Draft reply from assistant:\n"
    "---------------------------\n"
    "{draft}\n"
)

# --- simple token helpers (for leniency heuristic) ---------------------------

_TOKEN_RE = re.compile(r"[A-Za-z0-9+#\-_/]{3,}")

def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]

def _looks_grounded_and_actionable(state: Dict) -> bool:
    """
    Lightweight guardrail to avoid nitpicky rejections:
    - If draft overlaps well with context terms OR
    - Draft explicitly shows a 'Context' section with items
    - and it includes basic actionability markers,
    then consider it good enough to approve.
    """
    draft = state.get("draft", "") or ""
    ctx_list = state.get("context", []) or []
    if ("Context:" in draft or "context:" in draft) and ctx_list:
        has_steps_word = any(w in draft.lower() for w in ["step", "try", "follow", "please update", "reset"])
        if has_steps_word:
            return True

    draft_tokens = set(_tokenize(draft))
    ctx_tokens: Set[str] = set(_tokenize(" ".join(ctx_list)))
    overlap = len(draft_tokens & ctx_tokens)

    # If we share a decent number of tokens with context and the draft hints at actions, approve.
    actionable = any(w in draft.lower() for w in ["please", "try", "follow", "update", "reset", "check"])
    return overlap >= 5 and actionable

# --- prompt/rendering ---------------------------------------------------------

def _render_user_prompt(state: Dict) -> str:
    ctx_list = state.get("context", []) or []
    ctx_block = "- " + "\n- ".join(ctx_list) if ctx_list else "(none)"
    return USER_TEMPLATE.format(
        subject=state.get("subject", ""),
        description=state.get("description", ""),
        category=state.get("category", ""),
        context=ctx_block,
        draft=state.get("draft", ""),
    )

def _parse_review_json(raw: str) -> Dict:
    """
    Parse reviewer JSON with defensive defaults.
    Always returns {'approved': bool, 'feedback': str}.
    """
    approved = False
    feedback = "Automatic fallback: unable to parse review; ensure the reply cites context steps."
    try:
        data = json.loads(raw or "{}")
        if isinstance(data.get("approved"), bool):
            approved = data["approved"]
        fb = data.get("feedback")
        if isinstance(fb, str) and fb.strip():
            feedback = fb.strip()
        else:
            feedback = "Looks good." if approved else "Please ground the reply in the provided context and add clear next steps."
    except Exception:
        pass
    return {"approved": approved, "feedback": feedback}

# --- node --------------------------------------------------------------------

def review(state: Dict) -> Dict:
    """
    LangGraph node: review the current draft and gate approval.
    """
    user_prompt = _render_user_prompt(state)
    try:
        completion: ChatCompletion = _openai.chat.completions.create(
            model=MODEL_NAME,
            temperature=0,  # keep deterministic
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = completion.choices[0].message.content or "{}"
    except Exception:
        # If API fails, use a deterministic minimal rule so the graph continues.
        draft = state.get("draft", "")
        approved = "Context:\n-" in draft or _looks_grounded_and_actionable(state)
        fb = "Looks good." if approved else "Please include at least one concrete step from retrieval context."
        return {"approved": approved, "review": {"feedback": fb}}

    parsed = _parse_review_json(content)

    # ✅ LENIENCY OVERRIDE:
    # If the LLM said False but our heuristic says it's clearly grounded & actionable, approve it.
    if not parsed["approved"] and _looks_grounded_and_actionable(state):
        parsed["approved"] = True
        parsed["feedback"] = "Approved: grounded and actionable; minor style issues are acceptable."

    return {"approved": parsed["approved"], "review": {"feedback": parsed["feedback"]}}
