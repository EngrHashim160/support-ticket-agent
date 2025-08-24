"""
Ticket classifier (LLM-backed)

Why this file exists:
- Turn messy, real-world ticket text into a single category label the rest of the graph can route on.
- Keep the surface area tiny and the behavior predictable (strict JSON output, safe fallbacks).

Design notes:
- Deterministic prompting (temperature=0) for repeatability in CI.
- Strict JSON response to avoid brittle string parsing.
- Defensive parsing with a safe fallback ("General") so the graph never stalls.
"""

from __future__ import annotations

import json
from typing import Dict, Final, List

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletion

# --- bootstrap ---------------------------------------------------------------

# Load OPENAI_API_KEY from .env if present. Fails over to env var if running in CI.
load_dotenv()
_openai = OpenAI()  # relies on OPENAI_API_KEY

# --- constants ---------------------------------------------------------------

MODEL_NAME: Final[str] = "gpt-4o-mini"  # Swap to "gpt-4o" if you want more headroom.

# Keep categories simple & explicit to avoid "creative" outputs.
ALLOWED_CATEGORIES: Final[List[str]] = ["Billing", "Technical", "Security", "General"]

# System message keeps the model focused and constrains output shape.
SYSTEM_PROMPT: Final[str] = (
    "You are a precise support ticket classifier. "
    "Choose exactly ONE category from this allowed set: "
    f"{', '.join(ALLOWED_CATEGORIES)}. "
    'Return ONLY valid JSON like {"category":"Technical"} with no commentary.'
)

# The user template provides just enough context without leaking business logic.
USER_PROMPT_TEMPLATE: Final[str] = (
    "Subject: {subject}\n"
    "Description: {description}\n\n"
    "Rules:\n"
    f"- Pick one of: {', '.join(ALLOWED_CATEGORIES)}\n"
    "- If unsure, choose the closest fit (never respond with Unknown).\n"
)

# --- helpers -----------------------------------------------------------------


def _render_user_prompt(subject: str, description: str) -> str:
    """Format the user prompt with the incoming ticket fields."""
    return USER_PROMPT_TEMPLATE.format(subject=subject or "", description=description or "")


def _parse_model_json(raw_content: str) -> str:
    """
    Parse the model's JSON string safely and return a valid category.
    Any failure (bad JSON, unexpected category) falls back to 'General'.
    """
    try:
        data = json.loads(raw_content or "{}")
        category = str(data.get("category", "")).strip()
        if category in ALLOWED_CATEGORIES:
            return category
    except Exception:
        # Intentionally swallow parsing errors; we always return a safe label.
        pass
    return "General"


def _classify_with_openai(user_prompt: str) -> str:
    """
    Call OpenAI with strict settings to get a single category label.
    - temperature=0 for determinism.
    - response_format enforces JSON output.
    """
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
    return _parse_model_json(content)


# --- public API for the node -------------------------------------------------


def classify(state: Dict) -> Dict:
    """
    LangGraph node: classify the ticket into one category.

    Input (state):
        subject: str
        description: str

    Output (partial state update):
        {"category": "<Billing|Technical|Security|General>"}
    """
    subject = state.get("subject", "")
    description = state.get("description", "")

    # Keep the call minimal; upstream nodes can add more signals later if needed.
    user_prompt = _render_user_prompt(subject, description)

    # If the API is unavailable for any reason, we fail closed into "General"
    # so the graph can continue and we can inspect logs/telemetry later.
    try:
        chosen_category = _classify_with_openai(user_prompt)
    except Exception:
        chosen_category = "General"

    return {"category": chosen_category}
