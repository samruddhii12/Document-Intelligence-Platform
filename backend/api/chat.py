import os
from fastapi import APIRouter, HTTPException
from backend.services.text_extractor import extract_text
from backend.services.chunker import chunk_text
from backend.services.embeddings import generate_embeddings
from backend.services.vector_store import (
    create_faiss_index,
    save_faiss_index,
    search_index,
    load_faiss_index,
    rerank_chunks
)
from backend.services.llm import generate_answer
from pydantic import BaseModel

import json

router = APIRouter()

BASE_STORAGE = "backend/storage/sessions"

class ChatRequest(BaseModel):
    query: str
    top_k: int = 10


@router.get("/extract/{session_id}")
def extract_document_text(session_id: str):
    session_path = os.path.join(BASE_STORAGE, session_id)

    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")

    files = os.listdir(session_path)
    if not files:
        raise HTTPException(status_code=404, detail="No document found")

    file_path = os.path.join(session_path, files[0])

    try:
        text = extract_text(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "session_id": session_id,
        "characters": len(text),
        "preview": text[:1000]
    }


@router.get("/chunk/{session_id}")
def chunk_document(session_id: str):
    session_path = os.path.join(BASE_STORAGE, session_id)

    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")

    files = os.listdir(session_path)
    if not files:
        raise HTTPException(status_code=404, detail="No document found")

    file_path = os.path.join(session_path, files[0])

    text = extract_text(file_path)
    chunks = chunk_text(text)

    return {
        "session_id": session_id,
        "total_chunks": len(chunks),
        "sample_chunks": chunks[:3]
    }



@router.post("/embed/{session_id}")
def embed_document(session_id: str):
    session_path = os.path.join(BASE_STORAGE, session_id)

    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")

    files = os.listdir(session_path)
    if not files:
        raise HTTPException(status_code=404, detail="No document found")

    file_path = os.path.join(session_path, files[0])

    text = extract_text(file_path)
    chunks = chunk_text(text)

    embeddings = generate_embeddings(chunks)

    if embeddings.size == 0:
        raise HTTPException(status_code=400, detail="No text to embed")

    index = create_faiss_index(embeddings)

    # Save FAISS index
    index_path = os.path.join(session_path, "faiss.index")
    save_faiss_index(index, index_path)

    # Save chunks (important for retrieval later)
    chunks_path = os.path.join(session_path, "chunks.json")
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    return {
        "session_id": session_id,
        "total_chunks": len(chunks),
        "embedding_dimension": embeddings.shape[1]
    }


@router.post("/retrieve/{session_id}")
def retrieve_chunks(session_id: str, query: str):
    session_path = os.path.join(BASE_STORAGE, session_id)

    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")

    index_path = os.path.join(session_path, "faiss.index")
    chunks_path = os.path.join(session_path, "chunks.json")

    if not os.path.exists(index_path):
        raise HTTPException(status_code=400, detail="Embeddings not created")

    # Load FAISS
    index = load_faiss_index(index_path)

    # Load chunks
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    # Embed query
    query_embedding = generate_embeddings([query])

    # Search
    distances, indices = search_index(index, query_embedding)

    # retrieved_chunks = [chunks[i] for i in indices[0]]
    retrieved_chunks = [
    chunks[i] for i in indices[0]
    if i != -1 and i < len(chunks)
]

    return {
        "query": query,
        "top_k": len(retrieved_chunks),
        "results": retrieved_chunks
    }


@router.post("/chat/{session_id}")
def chat_with_document(session_id: str, payload: ChatRequest):
    session_path = os.path.join(BASE_STORAGE, session_id)

    if not os.path.exists(session_path):
        raise HTTPException(status_code=404, detail="Session not found")

    index_path = os.path.join(session_path, "faiss.index")
    chunks_path = os.path.join(session_path, "chunks.json")

    if not os.path.exists(index_path) or not os.path.exists(chunks_path):
        raise HTTPException(status_code=400, detail="Run /embed first")

    # Load FAISS
    index = load_faiss_index(index_path)

    # Load chunks
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    query = payload.query.strip()

    # Embed query
    query_embedding = generate_embeddings([query])

    # Search similar chunks
    # distances, indices = search_index(index, query_embedding, top_k=payload.top_k)

    # retrieved_chunks = [chunks[i] for i in indices[0] if i < len(chunks)]

    # context = "\n\n".join(retrieved_chunks)

    # # Call LLM
    # answer = generate_answer(context, query)
    # Step 1: search more chunks
    distances, indices = search_index(index, query_embedding, top_k=payload.top_k)

    retrieved_chunks = [
        chunks[i] for i in indices[0]
        if i != -1 and i < len(chunks)
    ]

# Step 2: rerank them
    best_chunks = rerank_chunks(query, retrieved_chunks, top_n=5)

    # Step 3: better context formatting
    context = "\n\n---\n\n".join(best_chunks)

    # Step 4: call LLM
    answer = generate_answer(context, query)
    history_path = os.path.join(session_path, "history.json")


    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    # Append new entry
    history.append({
        "question": query,
        "answer": answer,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    })

    # Save back
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return {
        "question": query,
        "answer": answer
    }
    
@router.get("/history/{session_id}")
def get_history(session_id: str):
    session_path = os.path.join(BASE_STORAGE, session_id)
    history_path = os.path.join(session_path, "history.json")

    if not os.path.exists(history_path):
        return {"session_id": session_id, "history": []}

    with open(history_path, "r", encoding="utf-8") as f:
        history = json.load(f)

    return {"session_id": session_id, "history": history}

