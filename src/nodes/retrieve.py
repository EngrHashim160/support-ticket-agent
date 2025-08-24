"""
Retrieve (category-aware + refine-aware)

Goal:
- Return the top few knowledge snippets for drafting.
- Prefer snippets that match the category and any refine hints from the reviewer.

Current implementation:
- Uses a small in-memory corpus (placeholder).
- Scores snippets by keyword overlap with `refine_hint` and ticket text.
- Returns the top 3. (We’ll swap this with FAISS in a later step.)
"""

from __future__ import annotations

from typing import Dict, List, Tuple
import re

# --- tiny placeholder corpora ------------------------------------------------
_CORPUS = {
    "Technical": [
        "Reset your password from Settings → Account → Reset Password.",
        "Ensure app version is latest; try clearing cache and retry.",
        "If email not received, check spam and rate limits.",
        "Mobile iOS: enable Background App Refresh for notifications.",
        "Android: clear storage via App Info → Storage → Clear Data (will log you out).",
    ],
    "Billing": [
        "Invoices are sent on the 1st of each month.",
        "Refunds follow policy section 3.2 (no partial refunds after 14 days).",
        "Update payment method under Billing → Payment Methods → Add Card.",
        "Charge disputes must be opened within 60 days from invoice date.",
    ],
    "Security": [
        "MFA required for admin roles; see Security Policy §4.",
        "Password rules: 12+ chars, mixed case, symbol.",
        "Reset 2FA via support with identity verification (government ID).",
        "Sessions auto-expire after 12 hours of inactivity.",
    ],
    "General": [
        "Thanks for contacting support; we’re here to help.",
        "Our help center covers account, billing, and security basics.",
        "Share screenshots to speed up troubleshooting.",
    ],
}

_TOKEN_RE = re.compile(r"[A-Za-z0-9+#\-_/]{3,}")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _score(snippet: str, query_terms: List[str]) -> float:
    """
    Simple overlap scorer:
    - +1 per matched term (substring-insensitive by token)
    - + bonus for longer snippets to mildly reward richer instructions
    """
    tokens = set(_tokenize(snippet))
    hits = sum(1 for t in query_terms if t in tokens)
    return hits + 0.05 * len(snippet)


def retrieve(state: Dict) -> Dict:
    """
    Inputs used:
      - category: str               -> selects the corpus bucket
      - subject, description: str   -> baseline query terms
      - refine_hint: str (optional) -> extra terms from reviewer feedback

    Output:
      - {"context": [top-3 snippets]}
    """
    category = state.get("category", "General")
    subject = state.get("subject", "")
    description = state.get("description", "")
    refine_hint = state.get("refine_hint", "")

    # Build query terms from ticket + refine signal.
    query_terms: List[str] = _tokenize(" ".join([subject, description, refine_hint]))

    # Pick the bucket by category; default to General if unknown.
    bucket: List[str] = _CORPUS.get(category, _CORPUS["General"])

    # Score and sort by relevance.
    ranked: List[Tuple[float, str]] = [(_score(sn, query_terms), sn) for sn in bucket]
    ranked.sort(key=lambda x: x[0], reverse=True)

    # Return top-3 snippets.
    top_snippets = [sn for _, sn in ranked[:3]]
    return {"context": top_snippets}