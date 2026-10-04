# Document Intelligence Platform — Complete Edition

A privacy-oriented document intelligence/RAG application built with FastAPI, Streamlit, PostgreSQL + pgvector, Sentence Transformers and a local Ollama LLM.

## Implemented roadmap

**Phase 1 — Persistence:** PostgreSQL, pgvector, documents, chunks, workspaces, chats and messages.

**Phase 2 — Grounded RAG:** page/section/chunk-aware sources, semantic retrieval and citations.

**Phase 3 — Identity & authorization:** signup/login, bcrypt, JWT, guest identities, user/guest workspace isolation, guest-to-account claim endpoint, logout and expiry handling.

**Phase 4 — Dashboard/history:** persistent workspaces, documents, chat sessions and resumable conversation history.

**Phase 5 — Multi-document workspaces:** many documents per workspace and document-scoped or workspace-wide Q&A.

**Phase 6 — Conversational memory:** bounded recent-message context for reference resolution; document context remains evidence.

**Phase 7 — Hybrid retrieval/evaluation:** pgvector semantic retrieval + BM25-style keyword retrieval using reciprocal-rank fusion. `eval/` contains a reproducible evaluation scaffold. No fake quality metrics are claimed.

**Phase 8 — Production foundation:** environment configuration, Docker Compose, CORS configuration, upload limits, logging, health endpoint, tests and isolated storage. Before internet deployment, add reverse-proxy TLS, a managed secret store, rate limiting at the gateway, monitoring and a full Alembic migration history.

**Phase 9 — Advanced intelligence:** summaries, suggested questions and document comparison endpoints. PDF/DOCX extraction is included. OCR dependencies are installed for extension to scanned PDFs; scanned-PDF fallback should be validated for your deployment before treating OCR as production-ready.

## Architecture

Browser → Streamlit → FastAPI → PostgreSQL/pgvector<br>
                         ↘ Ollama<br>
                         ↘ local document storage

Ownership is attached at the workspace level:
`User/Guest → Workspace → Documents → Chunks`
and
`Workspace → Chat Sessions → Messages`.

## Quick start (local)

1. Install PostgreSQL with pgvector and Ollama.
2. Pull a model, for example `ollama pull llama3.2:3b`.
3. Create `.env` using the configuration below and set a strong `JWT_SECRET_KEY`. Environment files are intentionally excluded from this repository.
4. Create the database and enable pgvector:
   `CREATE EXTENSION IF NOT EXISTS vector;`
5. Create and activate a Python 3.11 environment, then install packages: `python3.11 -m venv .venv`, `source .venv/bin/activate`, `python -m pip install -r requirements.txt`.
6. For local execution, set `DATABASE_URL` to your local PostgreSQL user/database and `OLLAMA_URL=http://127.0.0.1:11434/api/generate` in `.env`. Set `OLLAMA_MODEL` to an installed model shown by `ollama list`, and start Ollama with `ollama serve` if needed. For Docker, use `db` as the database host and `host.docker.internal` as the Ollama host.
7. Create tables: `.venv/bin/python -m backend.init_db`. On an existing database, also apply the SQL files in `migrations/` in filename order with `psql -v ON_ERROR_STOP=1 --single-transaction -f <file>` using your connection arguments. The initializer creates missing tables but does not alter existing ones.
8. Start backend: `.venv/bin/python -m uvicorn backend.main:app --reload`.
9. From the project root, create `.streamlit/secrets.toml` with `API_URL="http://127.0.0.1:8000"`.
10. In a separate terminal, start frontend: `.venv/bin/python -m streamlit run frontend/app.py`.

Example `.env` configuration (replace the placeholders):

```dotenv
DATABASE_URL=postgresql+psycopg2://YOUR_USER:YOUR_PASSWORD@localhost:5432/YOUR_DATABASE
JWT_SECRET_KEY=YOUR_RANDOM_SECRET_AT_LEAST_32_CHARACTERS
OLLAMA_URL=http://127.0.0.1:11434/api/generate
OLLAMA_MODEL=qwen2.5:3b
```

Generate a JWT secret with `python -c "import secrets; print(secrets.token_hex(32))"`.

Tests are retained locally and intentionally excluded from this repository. In the original development workspace, run the endpoint and frontend integration checks with `RUN_DB_TESTS=1 HF_HUB_OFFLINE=1 .venv/bin/python -m pytest -q`. These checks use `.env`, temporary uploaded files, and database transactions that are rolled back. They require PostgreSQL, a cached embedding model, and Ollama with the configured model installed.

## Docker

Ollama normally runs on the host. Then:

`docker compose up --build`

Open Streamlit at `http://localhost:8501`.

## Important security notes

Never commit `.env`. Rotate a JWT secret if it is ever exposed. Guest IDs are bearer credentials and must remain unguessable. All workspace/document/chat operations are owner checked. Production deployments should terminate HTTPS in front of the application and use a proper secret manager.

## Evaluation

Copy `eval/questions.example.json` to your own dataset. Use real documents and expected evidence. Evaluate retrieval recall, citation correctness, groundedness and answer relevance. Do not claim percentage improvements until measured.

## Current practical limitations

This package is a complete reference implementation, but production deployment still requires environment-specific validation. OCR/scanned PDFs, very large corpora, concurrency/load, model quality and RAG metrics depend on your machine, chosen Ollama model and documents. The code intentionally does not invent those results.
