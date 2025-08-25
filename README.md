# 🎫 Support Ticket Resolution Agent

An **Agentic RAG system** built with [LangGraph](https://github.com/langchain-ai/langgraph) that classifies support tickets, retrieves relevant knowledge base context, drafts responses, and runs them through a **multi-step review loop**. If two attempts fail, the ticket is **escalated** for human review.

---

## ✨ Features
- **Classification**: Categorizes tickets into *Technical*, *Billing*, *Security*, or *General*.  
- **RAG-powered retrieval**: Uses FAISS + OpenAI embeddings to fetch relevant context snippets.  
- **Drafting**: Generates empathetic, context-grounded replies.  
- **Review loop**: LLM-backed reviewer checks tone, groundedness, policy compliance, and actionability.  
- **Retries**: If rejected, the agent refines and retries (max 2).  
- **Escalation**: Tickets still failing after 2 retries are logged to `escalation_log.csv`.  
- **UI**: Streamlit frontend for interactive testing.  
- **Tests**: Pytest suite ensures happy path, retry, and escalation behavior.

---

## 🧩 Agent Flow
The following diagram shows the entire pipeline:

![Agent Flow](docs/agent_flow.mmd)

> Rendered via Mermaid — ensures clarity of the corrective loop and escalation path.

---

## 📂 Project Structure
```
support-ticket-agent/
├── src/                 # Core code (nodes, graph definition)
├── tests/               # Pytest test cases
├── rag_corpus/          # Knowledge base documents
├── rag_index/           # FAISS index
├── docs/agent_flow.mmd  # Mermaid diagram of the agent flow
├── escalation_log.csv   # Escalation records
├── app.py               # Streamlit UI
├── run_local.py         # Local CLI runner
├── requirements.txt     # Python dependencies
└── README.md            # You are here
```

---

## ⚡ Quickstart

### 1. Clone the repo
```bash
git clone https://github.com/EngrHashim160/support-ticket-agent.git
cd support-ticket-agent
```

### 2. Setup environment
```bash
python -m venv langgraph_env
source langgraph_env/bin/activate     # Linux/macOS
langgraph_env\Scripts\activate       # Windows

pip install -r requirements.txt
```

Set your OpenAI API key in `.env`:
```
OPENAI_API_KEY=sk-xxxx
```

### 3. Run locally (CLI)
```bash
python run_local.py
```

### 4. Launch UI
```bash
streamlit run app.py
```
Fill in a **Subject** and **Description** to simulate a ticket.  
You can also view and save the **Agent Flow Graph** directly from the UI.

### 5. Run tests
```bash
pytest -q
```

---

## ✅ Example
**Input:**  
_Subject:_ `Password reset not working on mobile`  
_Description:_ `User cannot reset password on iOS app.`  

**Output (approved):**
```json
{
  "category": "Technical",
  "context": [
    "Reset your password from Settings → Account → Reset Password.",
    "Ensure app version is latest; try clearing cache and retry.",
    "If email not received, check spam and rate limits."
  ],
  "draft": "Hi there, thanks for reaching out. ...",
  "review": { "feedback": "Looks good." },
  "approved": true,
  "attempts": 0
}
```

---

## 🛠️ Tech Stack
- [LangGraph](https://github.com/langchain-ai/langgraph)  
- [LangChain](https://www.langchain.com/)  
- [OpenAI GPT-4o / GPT-4o-mini](https://platform.openai.com/)  
- [FAISS](https://faiss.ai/)  
- [Streamlit](https://streamlit.io/)  
- [Pytest](https://pytest.org/)  

---

## 📌 Notes
- If `escalation_log.csv` grows, these should be routed to a human queue in production.  
- The diagram is generated automatically and stored in `docs/agent_flow.mmd`.  
- This repo demonstrates **Corrective RAG** patterns applied to support automation.

---

## 👨‍💻 Author
Built by [Hashim](https://github.com/EngrHashim160) as part of an industrial assessment project.

---
