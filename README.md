# Document Intelligence Platform

A privacy-first document summarization and Q&A system built with FastAPI, Streamlit, and local LLM integration using Ollama.

## Use Cases

- **Document Summarization** — Automatically extract and summarize key information from PDF and DOCX files
- **Intelligent Q&A** — Ask questions about your documents and get accurate answers based on document content
- **Multi-Document Search** — Search across multiple uploaded documents using semantic search
- **Privacy-First** — All processing happens locally; no data sent to external servers
- **Session Management** — Organize conversations by document sessions with persistent storage

## Features

- Upload PDF and DOCX documents
- Split documents into chunks for better context retrieval
- Generate embeddings using sentence transformers
- Semantic search using FAISS vector database
- Chat with documents using local Ollama LLM
- Delete sessions and manage documents
- RESTful API backend with CORS support
- Clean, modern Streamlit UI

## Requirements

### System Requirements
- Python 3.8+
- 4GB+ RAM (minimum)
- Ollama installed and running locally

### Dependencies
All Python dependencies are listed in `requirements.txt`:
```
fastapi, uvicorn, streamlit, sentence-transformers, faiss-cpu, langchain, etc.
```

## Quick Start

### 1. Clone/Extract the Project
```bash
cd "Document Intelligence Platform"
```

### 2. Create Virtual Environment
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# or
venv\Scripts\activate  # Windows CMD
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install & Run Ollama
```bash
# Download from https://ollama.ai
# After installation, pull the model:
ollama pull tinyllama
# Keep Ollama running in the background
```

### 5. Start Backend
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 6. Start Frontend (in new terminal)
```bash
cd Document Intelligence Platform
streamlit run frontend/app.py
```

### 7. Access the App
- Frontend: `http://localhost:8501`
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

## Project Structure

```
Document Intelligence Platform/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── api/
│   │   ├── upload.py          # Document upload endpoint
│   │   ├── chat.py            # Chat/Q&A endpoint
│   │   └── delete.py          # Session delete endpoint
│   ├── services/
│   │   ├── chunker.py         # Document chunking
│   │   ├── embeddings.py      # Embedding generation
│   │   ├── llm.py             # Ollama LLM integration
│   │   ├── text_extractor.py  # PDF/DOCX extraction
│   │   ├── vector_store.py    # FAISS management
│   │   └── summarizer.py      # Document summarization
│   ├── models/
│   │   └── schemas.py         # Pydantic models
│   ├── storage/
│   │   └── sessions/          # Session data & embeddings
│   └── utils/
│       └── cleanup.py         # Cleanup utilities
├── frontend/
│   └── app.py                 # Streamlit UI
└── requirements.txt           # Python dependencies
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/upload` | Upload document |
| POST | `/chat` | Chat with document |
| DELETE | `/delete/{session_id}` | Delete session |

## Configuration

### Change LLM Model
Edit `backend/services/llm.py`:
```python
MODEL_NAME = "tinyllama"  # Change to any installed Ollama model
```

Available Ollama models:
- `tinyllama` — Lightweight, fast (default)
- `llama2` — Better quality, slower
- `neural-chat` — Optimized for chat

### Customize Chunk Size
Edit `backend/services/chunker.py` to adjust document chunking behavior.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'streamlit'` | Run `pip install -r requirements.txt` |
| `Connection refused (localhost:11434)` | Ensure Ollama is running |
| `Model not found: tinyllama` | Run `ollama pull tinyllama` |
| `CORS error` | Backend CORS is enabled for all origins (localhost) |

## Performance Tips

- Use `tinyllama` for fast responses on CPU
- Increase chunk size for better context (harder on memory)
- Upload smaller documents first for testing
- Keep Ollama running in a separate terminal

## Future Enhancements

- [ ] Support for more document formats (Excel, PPT)
- [ ] Multi-language support
- [ ] User authentication
- [ ] Document versioning
- [ ] Export conversation history
- [ ] Custom prompt templates

## License

MIT

## Contact

For issues or questions, contact the development team.
