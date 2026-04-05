# DocMind — Document Intelligence Platform

A privacy-first document Q&A system that lets you upload any PDF or DOCX file and have a conversation with it — entirely on your local machine, no data sent anywhere.

---

## What It Does

Upload a document, ask questions in plain language, and get accurate answers grounded in the document's content. Everything runs locally using open-source models.

- **Document Q&A** — Ask anything about your uploaded document and get context-aware answers
- **Semantic Search** — Finds the most relevant sections of your document, not just keyword matches
- **Reranking** — Retrieved chunks are reranked by a cross-encoder for higher answer quality
- **Chat History** — Every Q&A session is saved per document and restored across page reloads
- **Session Management** — Each uploaded document gets its own isolated session with stored embeddings
- **Fully Local** — No API keys, no cloud, no data leaves your machine

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Backend | FastAPI |
| Embeddings | `sentence-transformers` (all-mpnet-base-v2) |
| Vector Search | FAISS |
| Reranking | CrossEncoder (ms-marco-MiniLM-L-6-v2) |
| LLM | Ollama (tinyllama by default) |
| Text Extraction | pypdf, python-docx |
| Tokenization | tiktoken |

---

## Quick Start

**1. Create and activate a virtual environment**
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows PowerShell
source venv/bin/activate       # macOS / Linux
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Install Ollama and pull the model**
```bash
# Download from https://ollama.ai, then:
ollama pull tinyllama
```

**4. Start the backend**
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**5. Start the frontend** (new terminal)
```bash
streamlit run frontend/app.py
```

**6. Open in browser**
- App → `http://localhost:8501`
- API docs → `http://localhost:8000/docs`

---

## How It Works

1. **Upload** — File is saved to a unique session folder on disk
2. **Embed** — Document is extracted, split into overlapping token chunks, and embedded using a sentence transformer model
3. **Index** — Embeddings are stored in a FAISS index alongside the raw chunks
4. **Query** — Your question is embedded, top-K similar chunks are retrieved from FAISS, reranked by a cross-encoder, and passed as context to the LLM
5. **Answer** — The local Ollama model generates an answer strictly based on the retrieved context
6. **History** — Each Q&A pair is appended to a `history.json` file inside the session folder

---

## Codebase

```
DocMind/
├── backend/
│   ├── main.py                 # FastAPI app entry point, router registration
│   ├── api/
│   │   ├── upload.py           # POST /upload — saves file, creates session
│   │   ├── chat.py             # POST /embed, POST /chat, GET /history
│   │   └── delete.py           # DELETE /session/{id} — wipes session folder
│   ├── services/
│   │   ├── text_extractor.py   # Extracts text from PDF and DOCX
│   │   ├── chunker.py          # Paragraph-aware token chunking with overlap
│   │   ├── embeddings.py       # Generates embeddings via sentence-transformers
│   │   ├── vector_store.py     # FAISS index creation, search, and reranking
│   │   └── llm.py              # Sends prompt + context to local Ollama model
│   ├── models/
│   │   └── schemas.py          # Pydantic request/response schemas
│   ├── storage/
│   │   └── sessions/           # Per-session folders: file, chunks, index, history
│   └── utils/
│       └── cleanup.py          # Deletes session folder on request
└── frontend/
    └── app.py                  # Streamlit UI — upload, chat, history display
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/upload` | Upload a PDF or DOCX file |
| POST | `/embed/{session_id}` | Extract, chunk, and index the document |
| POST | `/chat/{session_id}` | Ask a question, get an answer |
| GET | `/history/{session_id}` | Fetch saved Q&A history for a session |
| DELETE | `/session/{session_id}` | Delete session and all associated data |

---

## Configuration

**Change the LLM model** in `backend/services/llm.py`:
```python
MODEL_NAME = "tinyllama"  # any model pulled via ollama
```

**Change chunk size** in `backend/services/chunker.py`:
```python
chunk_size = 500   # tokens per chunk
overlap    = 100   # token overlap between chunks
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Connection refused (port 11434)` | Start Ollama — it must be running in the background |
| `Model not found: tinyllama` | Run `ollama pull tinyllama` |
| Slow first response | Models and embeddings load once on startup; subsequent calls are faster |
| Empty answers | Try rephrasing your question or increasing `top_k` in the chat request |