"""
Retrieve (FAISS-backed, category-aware, refine-aware)

What this does:
- Loads a FAISS vector index for the chosen category.
- Builds a query from subject + description + (optional) refine_hint.
- Returns the top-3 snippets' page_content as `context`.

Design notes:
- Indexes are created by:  python -m src.rag_ingest
- We cache loaded indexes per category for speed.
- If an index is missing/unavailable, we fall back to a tiny built-in corpus so the graph never stalls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Final, List, Optional

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings

# --- config ------------------------------------------------------------------

load_dotenv()  # uses your OPENAI_API_KEY from .env

_BASE_DIR: Final[Path] = Path(__file__).resolve().parents[2]  # project root
_INDEX_DIR: Final[Path] = _BASE_DIR / "rag_index"
_CATEGORIES: Final[List[str]] = ["Billing", "Technical", "Security", "General"]

# Cache of loaded FAISS stores: {"Category": FAISS}
_VDB_CACHE: Dict[str, FAISS] = {}

# Minimal fallback corpus so the app keeps running if no index is present.
_FALLBACK = {
    "Technical": [
        "Reset your password from Settings → Account → Reset Password.",
        "Ensure app version is latest; try clearing cache and retry.",
        "If email not received, check spam and rate limits.",
    ],
    "Billing": [
        "Invoices are sent on the 1st of each month.",
        "Refunds follow policy section 3.2 (no partial refunds after 14 days).",
    ],
    "Security": [
        "MFA required for admin roles; see Security Policy §4.",
        "Password rules: 12+ chars, mixed case, symbol.",
    ],
    "General": [
        "Thanks for contacting support; we’re here to help.",
        "Share screenshots to speed up troubleshooting.",
    ],
}


# --- helpers -----------------------------------------------------------------


def _index_path_for(category: str) -> Path:
    """Return the on-disk folder where the FAISS index for this category lives."""
    cat = category if category in _CATEGORIES else "General"
    return _INDEX_DIR / cat


def _get_or_load_store(category: str) -> Optional[FAISS]:
    """
    Load a FAISS store for the category, with module-level caching.
    Returns None if the index folder is missing.
    """
    cat = category if category in _CATEGORIES else "General"
    if cat in _VDB_CACHE:
        return _VDB_CACHE[cat]

    index_dir = _index_path_for(cat)
    if not index_dir.exists():
        return None

    # Embedding model must match the one used at ingest (OpenAIEmbeddings).
    embeddings = OpenAIEmbeddings()
    # In newer langchain versions, set allow_dangerous_deserialization=True to load local indexes safely.
    store = FAISS.load_local(str(index_dir), embeddings, allow_dangerous_deserialization=True)
    _VDB_CACHE[cat] = store
    return store


def _build_query(state: Dict) -> str:
    """Compose a simple text query from ticket fields + refine hint."""
    subject = state.get("subject", "") or ""
    description = state.get("description", "") or ""
    refine_hint = state.get("refine_hint", "") or ""
    # Keep it compact but expressive. Order matters slightly for retrievers.
    return " ".join(part for part in [subject, description, refine_hint] if part).strip()


# --- node implementation -----------------------------------------------------


def retrieve(state: Dict) -> Dict:
    """
    Inputs used:
        - category: str
        - subject: str
        - description: str
        - refine_hint: str (optional, from reviewer feedback)

    Output:
        - {"context": [top-3 snippet strings]}
    """
    category = state.get("category", "General") or "General"
    query = _build_query(state)

    store = _get_or_load_store(category)
    if store:
        # Vector search over the category index
        docs = store.similarity_search(query, k=3)
        context = [d.page_content.strip() for d in docs if (d.page_content or "").strip()]
        # If the index returns nothing (edge case), use fallback so draft isn't empty.
        if context:
            return {"context": context}

    # Fallback: tiny in-memory corpus (keeps the pipeline robust)
    fallback_snippets = _FALLBACK.get(category, _FALLBACK["General"])
    return {"context": fallback_snippets[:3]}
