"""
FAISS ingestion (category-aware)

Reads small text/markdown docs from ./rag_corpus/<Category>/*
Builds an embedding index per category and saves them under ./rag_index/<Category>.

Run once locally:
    python -m src.rag_ingest
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document

load_dotenv()  # needs OPENAI_API_KEY

BASE = Path(__file__).resolve().parent.parent
CORPUS_DIR = BASE / "rag_corpus"
INDEX_DIR = BASE / "rag_index"
CATEGORIES = ["Billing", "Technical", "Security", "General"]

def _load_texts(folder: Path) -> List[Tuple[str, str]]:
    """Return list of (path, text) for all .txt/.md files in folder."""
    out: List[Tuple[str, str]] = []
    if not folder.exists():
        return out
    for p in folder.rglob("*"):
        if p.suffix.lower() in {".txt", ".md"} and p.is_file():
            out.append((str(p), p.read_text(encoding="utf-8", errors="ignore")))
    return out

def _build_index(category: str, docs: List[Tuple[str, str]]) -> None:
    """Create FAISS index for a category and persist it."""
    if not docs:
        print(f"[{category}] no docs, skipping.")
        return
    embedding = OpenAIEmbeddings()  # uses OPENAI_API_KEY
    lang_docs = [Document(page_content=txt, metadata={"path": path, "category": category}) for path, txt in docs]
    vectordb = FAISS.from_documents(lang_docs, embedding)
    outdir = INDEX_DIR / category
    outdir.mkdir(parents=True, exist_ok=True)
    vectordb.save_local(str(outdir))
    print(f"[{category}] indexed {len(docs)} docs → {outdir}")

def main() -> None:
    os.makedirs(INDEX_DIR, exist_ok=True)
    any_built = False
    for cat in CATEGORIES:
        folder = CORPUS_DIR / cat
        pairs = _load_texts(folder)
        _build_index(cat, pairs)
        any_built = any_built or bool(pairs)
    if not any_built:
        print("No docs found. Create some files under ./rag_corpus/<Category>/*.md or *.txt and re-run.")

if __name__ == "__main__":
    main()
