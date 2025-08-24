"""
Refine (feedback-aware)

Goal:
- Convert reviewer feedback + ticket text into retrieval hints for the next pass.
- Stay dependency-free and deterministic.

Contract:
Input  (state): subject, description, category, review.feedback, attempts
Output (update): {"refine_hint": str, "context": []}  # clear context so retrieve() re-runs fresh
"""

from __future__ import annotations

import re
from typing import Dict, Final, Iterable, List, Set


# --- simple keywording -------------------------------------------------------

_STOPWORDS: Final[Set[str]] = {
    # minimal list — enough to clean signal without external libs
    "the","a","an","and","or","but","if","then","else","so","to","for","of","on","in","at","by",
    "is","are","was","were","be","been","being","it","this","that","these","those",
    "with","without","from","as","about","into","over","under","again","further",
    "can","cannot","could","should","would","will","won't","dont","does","did","done",
    "user","customer","please","thanks","thank","hi","hello","issue","problem","error"
}

_TOKEN_RE: Final[re.Pattern] = re.compile(r"[A-Za-z0-9+#\-_/]{3,}")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _keywords(corpus: Iterable[str], keep: int = 8) -> List[str]:
    """
    Very small, local keyword extractor:
    - tokenizes
    - drops stopwords
    - favors longer tokens and those with symbols (e.g., 2fa, ios, reset_password)
    - returns top-N unique terms in order of appearance weight
    """
    seen: Set[str] = set()
    scored: List[tuple[str, float]] = []
    for text in corpus:
        for tok in _tokenize(text):
            if tok in _STOPWORDS or tok in seen:
                continue
            score = len(tok) + (2.0 if any(ch.isdigit() for ch in tok) else 0.0) + (1.5 if any(ch in "+#_/-" for ch in tok) else 0.0)
            scored.append((tok, score))
            seen.add(tok)
    # sort by score (desc), keep first N
    scored.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in scored[:keep]]


# --- node implementation -----------------------------------------------------


def refine(state: Dict) -> Dict:
    """
    Build a retrieval hint string using:
      - reviewer feedback (primary signal)
      - ticket subject/description (secondary)
      - category (to anchor vocabulary)
    """
    feedback = (state.get("review", {}) or {}).get("feedback", "")
    subject = state.get("subject", "")
    description = state.get("description", "")
    category = state.get("category", "")

    # Extract high-signal keywords
    terms = _keywords([feedback, subject, description, category], keep=10)

    # Compose a compact hint string the retriever can use next time.
    # (Next step we'll make retrieve.py consume this via boosted search / FAISS.)
    refine_hint = " ".join(terms) if terms else (category or "general")

    # Clear old context so the retrieval node fetches fresh chunks on the next hop.
    # We return only the fields we want to update; LangGraph merges this into state.
    return {
        "refine_hint": refine_hint,
        "context": []
    }
