"""
Reviewer (LLM-backed, simple & strict enough)

- Checks a couple of obvious policy rules up front (deterministic).
- Otherwise asks the LLM to review the draft for: grounding, policy, tone, actionability.
- Returns: {"approved": bool, "review": {"feedback": str}}
"""

from __future__ import annotations

import json
from typing import Dict, Final

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion

# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #

load_dotenv()
_openai = OpenAI()

MODEL_NAME: Final[str] = "gpt-4o-mini"  # use "gpt-4o" if you prefer

SYSTEM_PROMPT: Final[str] = (
    "You are a support reply reviewer.\n"
    "Approve ONLY if ALL are true:\n"
    "1) Grounded: draft uses a concrete fact from context (e.g., '14 days', a named feature, or a policy section).\n"
    "2) Policy-safe: no promises beyond policy. If a request is outside the policy window, the draft clearly says so.\n"
    "3) Tone: empathetic, concise, professional.\n"
    "4) Actionable: includes a clear step or next question.\n\n"
    "Return ONLY JSON: {\"approved\": bool, \"feedback\": \"...\"}.\n"
    "If you reject, keep feedback short and actionable."
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


# --------------------------------------------------------------------------- #
# Small helper: render prompt
# --------------------------------------------------------------------------- #

def _render_user_prompt(state: Dict) -> str:
    ctx_list = state.get("context") or []
    ctx_block = "- " + "\n- ".join(ctx_list) if ctx_list else "(none)"
    return USER_TEMPLATE.format(
        subject=state.get("subject", ""),
        description=state.get("description", ""),
        category=state.get("category", ""),
        context=ctx_block,
        draft=state.get("draft", ""),
    )


# --------------------------------------------------------------------------- #
# Hard-rule checks (deterministic, very simple)
# --------------------------------------------------------------------------- #

def _policy_guardrail(state: Dict) -> str | None:
    """
    Reject obvious refund-policy issues without calling the LLM.

    Rules:
      - If the user talks about a *refund* and the context mentions a 14-day window,
        then the draft must clearly mention that window (e.g., '14 days' or 'two weeks').
      - If the draft promises an 'immediate' or 'full' refund without citing a policy limit,
        reject it.
    Returns:
      None if OK, else a short feedback string explaining the rejection.
    """
    subject = (state.get("subject") or "").lower()
    description = (state.get("description") or "").lower()
    user_text = subject + " " + description

    draft = (state.get("draft") or "").lower()
    context_text = " ".join(state.get("context") or []).lower()

    user_mentions_refund = "refund" in user_text
    context_has_14_day = (("14" in context_text and "day" in context_text) or "two week" in context_text)

    # If refund is being asked and policy has a 14-day window, the draft must name it
    if user_mentions_refund and context_has_14_day:
        draft_mentions_window = (("14" in draft and "day" in draft) or "two week" in draft)
        if not draft_mentions_window:
            return "Refund request: please mention the 14-day (two-week) policy window explicitly."

    # Don't allow promises that aren't grounded in a policy limit
    if "refund" in draft and ("immediate refund" in draft or "full refund" in draft):
        if not (("14" in draft and "day" in draft) or "two week" in draft):
            return "Do not promise refunds without citing the policy limit (e.g., 14 days)."

    return None


# --------------------------------------------------------------------------- #
# Safe JSON parse
# --------------------------------------------------------------------------- #

def _parse_json_or_default(raw: str) -> Dict:
    """Always return {'approved': bool, 'feedback': str}."""
    approved = False
    feedback = "Unable to parse review; please cite a concrete policy detail (e.g., '14 days') and add a clear next step."
    try:
        data = json.loads(raw or "{}")
        if isinstance(data.get("approved"), bool):
            approved = data["approved"]
        fb = data.get("feedback")
        if isinstance(fb, str) and fb.strip():
            feedback = fb.strip()
        else:
            feedback = "Looks good." if approved else "Please cite a concrete policy detail and add a clear next step."
    except Exception:
        pass
    return {"approved": approved, "feedback": feedback}


# --------------------------------------------------------------------------- #
# Node: review
# --------------------------------------------------------------------------- #

def review(state: Dict) -> Dict:
    """
    LangGraph node: review the current draft and gate approval.
    """
    # 1) Quick policy guardrail (deterministic)
    violation = _policy_guardrail(state)
    if violation:
        return {"approved": False, "review": {"feedback": violation}}

    # 2) Ask the LLM to review
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
        parsed = _parse_json_or_default(content)
        return {"approved": parsed["approved"], "review": {"feedback": parsed["feedback"]}}
    except Exception:
        # 3) Fallback if API fails: very small rule set
        draft = (state.get("draft") or "").lower()
        context_text = " ".join(state.get("context") or []).lower()
        has_concrete_detail = any(x in draft for x in ["14 day", "14-day", "two week", "section"])
        has_action = any(x in draft for x in ["please", "try", "follow", "update", "reset", "check", "contact"])

        approved = bool(has_concrete_detail and has_action)
        feedback = (
            "Looks good."
            if approved
            else "Reject: please cite a concrete policy detail (e.g., '14 days') and include a clear next step."
        )
        return {"approved": approved, "review": {"feedback": feedback}}
