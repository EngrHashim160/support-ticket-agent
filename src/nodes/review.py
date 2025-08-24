"""
Reviewer (LLM-backed)

Goal:
- Evaluate the draft for groundedness, policy compliance, tone, and actionability.
- Return a simple gate: approved = True/False, plus actionable feedback for retries.

Contract:
Input  (state):  subject, description, category, context[], draft
Output (state):  {"approved": bool, "review": {"feedback": str}}
"""

from __future__ import annotations

import json
from typing import Dict, Final

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion

# --- bootstrap ---------------------------------------------------------------

load_dotenv()
_openai = OpenAI()

MODEL_NAME: Final[str] = "gpt-4o-mini"  # tune to "gpt-4o" if you prefer

SYSTEM_PROMPT: Final[str] = (
    "You are a strict support reply reviewer. "
    "Assess the assistant draft against four checks:\n"
    "1) Groundedness: Only uses given context; cites concrete steps.\n"
    "2) Policy: No refunds/promises beyond policy; no security leaks.\n"
    "3) Tone: Empathetic, concise, professional.\n"
    "4) Actionability: Clear next steps or questions.\n\n"
    "Return ONLY JSON with keys: approved (true/false) and feedback (string). "
    "Feedback must be short, actionable, and explain what to change if not approved."
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
    feedback = "Automatic fallback: unable to parse review; please ensure the draft cites context steps."
    try:
        data = json.loads(raw or "{}")
        if isinstance(data.get("approved"), bool):
            approved = data["approved"]
        fb = data.get("feedback")
        if isinstance(fb, str) and fb.strip():
            feedback = fb.strip()
        else:
            if approved:
                feedback = "Looks good."
            else:
                feedback = "Please ground the reply in the provided context and add clear next steps."
    except Exception:
        # keep defaults
        pass
    return {"approved": approved, "feedback": feedback}

def review(state: Dict) -> Dict:
    """
    LangGraph node: review the current draft and gate approval.
    """
    user_prompt = _render_user_prompt(state)
    try:
        completion: ChatCompletion = _openai.chat.completions.create(
            model=MODEL_NAME,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = completion.choices[0].message.content or "{}"
    except Exception:
        # Hard fallback: if API fails, do a minimal deterministic rule so the graph continues.
        draft = state.get("draft", "")
        approved = "Context:\n-" in draft
        fb = "Looks good." if approved else "Please include at least one concrete step from retrieval context."
        return {"approved": approved, "review": {"feedback": fb}}

    parsed = _parse_review_json(content)
    return {"approved": False, "review": {"feedback": parsed["feedback"]}}

# parsed["approved"]