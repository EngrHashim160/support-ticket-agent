"""
Streamlit UI for the Support Ticket Agent (LangGraph)

Features:
- Subject/Description form → runs the LangGraph pipeline
- Shows Category, Context, Draft, Reviewer Feedback, Attempts
- Mermaid-based graph viewer (no pygraphviz needed)
  - Buttons: Show Graph, Save Mermaid to docs/agent_flow.mmd
  - Controls: Height, Zoom, Theme
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import streamlit as st

from src.graph import build_graph

# ---------------- App bootstrap ----------------

st.set_page_config(page_title="Support Ticket Agent", page_icon="🎫", layout="centered")
st.title("🎫 Support Ticket Resolution Agent")
st.caption("Corrective RAG • LangGraph • FAISS • LangGraph")

# Build graph once per process
GRAPH = build_graph()

# Session-stable thread id for the checkpointer
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"ui-{uuid.uuid4().hex[:8]}"

# ---------------- Ticket form ----------------

with st.form("ticket_form", clear_on_submit=False):
    subject = st.text_input("Subject", placeholder="e.g., Password reset not working on mobile")
    description = st.text_area("Description", height=160, placeholder="Describe the issue in a few lines…")
    submitted = st.form_submit_button("Run Agent")

def _pretty(o):
    try:
        return json.dumps(o, indent=2, ensure_ascii=False)
    except Exception:
        return str(o)

if submitted:
    if not subject.strip() or not description.strip():
        st.warning("Please fill both Subject and Description.")
        st.stop()

    with st.spinner("Running agent…"):
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        initial_state = {
            "subject": subject.strip(),
            "description": description.strip(),
            "attempts": 0,
            "approved": False,
        }
        final_state = GRAPH.invoke(initial_state, config=config)

    # ---------------- Results ----------------
    st.subheader("Result")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Approved", "✅ Yes" if final_state.get("approved") else "❌ No")
        st.metric("Attempts", str(final_state.get("attempts", 0)))
    with col2:
        st.metric("Category", final_state.get("category", "—"))

    st.markdown("### Retrieved Context")
    ctx = final_state.get("context") or []
    if ctx:
        for i, snippet in enumerate(ctx, 1):
            st.write(f"**{i}.** {snippet}")
    else:
        st.info("No context returned.")

    st.markdown("### Draft Reply")
    st.code(final_state.get("draft") or "(no draft)", language="markdown")

    st.markdown("### Reviewer Feedback")
    fb = (final_state.get("review") or {}).get("feedback") or "(no feedback)"
    st.write(fb)

    if final_state.get("attempts", 0) >= 2 and not final_state.get("approved", False):
        st.error("Escalated after two failed attempts. Check `escalation_log.csv` in the repo root.")

# ---------------- Mermaid graph rendering (no pygraphviz needed) ----------------

st.divider()
st.subheader("🗺️ Agent Flow Diagram")

def render_mermaid(mermaid_code: str, height: int = 900, zoom: float = 1.0, theme: str = "default"):
    """
    Render Mermaid code in Streamlit using a lightweight HTML component.
    - height: iframe height in px
    - zoom: CSS scale factor (e.g., 0.8 to fit more; 1.2 to zoom in)
    - theme: 'default' | 'neutral' | 'dark'
    """
    from streamlit.components.v1 import html
    html(
        f"""
        <div style="transform: scale({zoom}); transform-origin: top left;">
          <div class="mermaid">
          {mermaid_code}
          </div>
        </div>
        <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, securityLevel: 'loose', theme: '{theme}' }});
        </script>
        """,
        height=int(height * zoom),
        scrolling=True,
    )

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    show_mermaid = st.button("Show Graph (Mermaid)")
with col2:
    save_mermaid = st.button("Save to docs/agent_flow.mmd")
with col3:
    height_px = st.number_input("Height (px)", min_value=500, max_value=3000, value=1200, step=100)

zoom = st.slider("Zoom (%)", min_value=50, max_value=150, value=80, step=5) / 100.0
theme = st.selectbox("Theme", options=["default", "neutral", "dark"], index=0)

def export_mermaid() -> str:
    code = GRAPH.get_graph().draw_mermaid()  # provided by LangGraph
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "agent_flow.mmd").write_text(code, encoding="utf-8")
    return code

if show_mermaid or save_mermaid:
    with st.spinner("Generating Mermaid diagram…"):
        mermaid_text = export_mermaid()
    if show_mermaid:
        render_mermaid(mermaid_text, height=int(height_px), zoom=zoom, theme=theme)
        st.caption("Rendered via Mermaid — resize with Height/Zoom if anything is clipped.")
    if save_mermaid:
        st.success("Saved to docs/agent_flow.mmd")

# ---------------- Sidebar ----------------

with st.sidebar:
    st.header("ℹ️ About")
    st.write(
        "This UI runs the same LangGraph pipeline used in tests:\n"
        "- Classify → Retrieve (FAISS) → Draft → Review\n"
        "- If rejected: Refine → Retrieve → Draft → Review (max 2 attempts)\n"
        "- After 2 failed tries: Escalate to CSV"
    )
    st.caption(f"Thread ID: `{st.session_state.thread_id}`")
    log_path = Path("escalation_log.csv")
    if log_path.exists():
        st.download_button(
            "Download escalation_log.csv",
            data=log_path.read_bytes(),
            file_name="escalation_log.csv",
            mime="text/csv",
        )
