from fastapi import APIRouter, HTTPException
from backend.services.text_extractor import (
    extract_text,
    extract_document_segments,
)

from backend.services.chunker import (
    chunk_text,
    chunk_segments,
)
from backend.services.embeddings import generate_embeddings
from backend.services.vector_store import rerank_chunks
from backend.services.llm import generate_answer
from pydantic import BaseModel

from backend.config import (
    STORAGE_DIR,
    RETRIEVAL_TOP_K,
    RERANK_TOP_N,
)

from backend.services.storage import (
    get_document_path,
    session_exists,
)
from backend.repositories.chat_repo import (
    add_message,
    get_messages,
    get_or_create_chat_session,
)
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db

from backend.repositories.chunk_repo import (
    create_chunks_bulk,
    delete_document_chunks, search_similar_chunks
)

from backend.repositories.doc_repo import (
    get_document,
    update_document_status,
)

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    top_k: int = RETRIEVAL_TOP_K

@router.get("/extract/{session_id}")
def extract_document_text(session_id: str):
    if not session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    try:
        file_path = get_document_path(session_id)
        text = extract_text(str(file_path))

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to extract document text",
        ) from exc

    return {
        "session_id": session_id,
        "characters": len(text),
        "preview": text[:1000],
    }

@router.get("/chunk/{session_id}")
def chunk_document(session_id: str):
    if not session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    try:
        file_path = get_document_path(session_id)
        text = extract_text(str(file_path))
        chunks = chunk_text(text)

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "session_id": session_id,
        "total_chunks": len(chunks),
        "sample_chunks": chunks[:3],
    }

@router.post("/embed/{session_id}")
def embed_document(
    session_id: str,
    db: Session = Depends(get_db),
):
    if not session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    try:
        document_id = UUID(session_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid document/session ID",
        ) from exc

    document = get_document(
        db=db,
        document_id=document_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found in database",
        )

    try:
        update_document_status(
            db=db,
            document_id=document_id,
            status="processing",
        )

        # file_path = get_document_path(session_id)

        # text = extract_text(str(file_path))
        # chunks = chunk_text(text)

        # if not chunks:
        #     raise HTTPException(
        #         status_code=400,
        #         detail="No text chunks generated",
        #     )

        # embeddings = generate_embeddings(chunks)
        file_path = get_document_path(session_id)

        segments = extract_document_segments(
            str(file_path)
        )

        chunks = chunk_segments(segments)

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No text chunks generated",
            )

        chunk_contents = [
            chunk["content"]
            for chunk in chunks
        ]

        embeddings = generate_embeddings(
            chunk_contents
        )

        if embeddings.size == 0:
            raise HTTPException(
                status_code=400,
                detail="No embeddings generated",
            )

        # Remove existing chunks if the document
        # is being embedded again.
        delete_document_chunks(
            db=db,
            document_id=document_id,
        )

        # Save chunks + embeddings to PostgreSQL/pgvector
        create_chunks_bulk(
            db=db,
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
        )

        update_document_status(
            db=db,
            document_id=document_id,
            status="indexed",
        )

    except HTTPException:
        update_document_status(
            db=db,
            document_id=document_id,
            status="failed",
        )
        raise

    except FileNotFoundError as exc:
        update_document_status(
            db=db,
            document_id=document_id,
            status="failed",
        )

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        update_document_status(
            db=db,
            document_id=document_id,
            status="failed",
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to process document",
        ) from exc

    return {
        "session_id": session_id,
        "document_id": str(document_id),
        "total_chunks": len(chunks),
        "embedding_dimension": embeddings.shape[1],
        "status": "indexed",
    }



@router.post("/retrieve/{session_id}")
def retrieve_chunks(
    session_id: str,
    query: str,
    db: Session = Depends(get_db),
):
    try:
        document_id = UUID(session_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid document/session ID",
        ) from exc

    document = get_document(
        db=db,
        document_id=document_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    query = query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty",
        )

    query_embedding = generate_embeddings([query])[0]

    results = search_similar_chunks(
        db=db,
        document_id=document_id,
        query_embedding=query_embedding,
        top_k=RETRIEVAL_TOP_K,
    )

    return {
        "query": query,
        "top_k": len(results),
        "results": [
            {
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
            "section_title": chunk.section_title,
                "content": chunk.content,
                "distance": distance,
                "similarity": 1 - distance,
            }
            for chunk, distance in results
        ],
    }


@router.post("/chat/{session_id}")
def chat_with_document(
    session_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
):
    try:
        document_id = UUID(session_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid document/session ID",
        ) from exc

    document = get_document(
        db=db,
        document_id=document_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if document.status != "indexed":
        raise HTTPException(
            status_code=400,
            detail="Document has not been indexed",
        )

    query = payload.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty",
        )

    # ----------------------------------------
    # 1. Generate query embedding
    # ----------------------------------------

    query_embedding = generate_embeddings([query])[0]

    # ----------------------------------------
    # 2. pgvector similarity search
    # ----------------------------------------

    results = search_similar_chunks(
        db=db,
        document_id=document_id,
        query_embedding=query_embedding,
        top_k=payload.top_k,
    )

    retrieved_chunks = [
    {
        "content": chunk.content,
        "chunk_index": chunk.chunk_index,
        "page_number": chunk.page_number,
        "section_title": chunk.section_title,
        "file_name": document.filename,
    }
    for chunk, _ in results
]

    if not retrieved_chunks:
        raise HTTPException(
            status_code=404,
            detail="No relevant chunks found",
        )

    # ----------------------------------------
    # 3. CrossEncoder reranking
    # ----------------------------------------
    rerank_input = [
    chunk["content"]
    for chunk in retrieved_chunks
]
    best_chunks = rerank_chunks(
        query,
        rerank_input,
        top_n=RERANK_TOP_N,
    )
    best_chunk_records = []

    for best_content in best_chunks:
        for chunk in retrieved_chunks:
            if chunk["content"] == best_content:
                best_chunk_records.append(chunk)
                break

    # ----------------------------------------
    # 4. Build LLM context
    # ----------------------------------------

    context_parts = []

    for chunk in best_chunk_records:
        source_parts = [chunk["file_name"]]

        if chunk["page_number"] is not None:
            source_parts.append(
                f"Page {chunk['page_number']}"
            )

        if chunk["section_title"]:
            source_parts.append(
                f"Section: {chunk['section_title']}"
            )

        source_parts.append(
            f"Chunk {chunk['chunk_index']}"
        )

        source_label = " | ".join(source_parts)

        context_parts.append(
            f"[Source: {source_label}]\n"
            f"{chunk['content']}"
        )

    context = "\n\n---\n\n".join(context_parts)
    # ----------------------------------------
    # 5. Generate answer
    # ----------------------------------------

    answer = generate_answer(
        context,
        query,
    )
    sources = [
    {
        "file_name": chunk["file_name"],
        "chunk_index": chunk["chunk_index"],
        "page_number": chunk["page_number"],
        "section_title": chunk["section_title"],
    }
    for chunk in best_chunk_records
]

    # ----------------------------------------
    # 6. Existing history system
    # Temporary — we'll move this to DB next
    # ----------------------------------------

    chat_session = get_or_create_chat_session(
    db=db,
    chat_session_id=document_id,
    workspace_id=document.workspace_id,
    )

    add_message(
        db=db,
        chat_session_id=chat_session.id,
        role="user",
        content=query,
    )

    add_message(
        db=db,
        chat_session_id=chat_session.id,
        role="assistant",
        content=answer,
        sources=sources,
    )
    return {
        "question": query,
        "answer": answer,
        "sources": sources,
    }


@router.get("/history/{session_id}")
def get_history(
    session_id: str,
    db: Session = Depends(get_db),
):
    try:
        chat_session_id = UUID(session_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid chat/session ID",
        ) from exc

    messages = get_messages(
        db=db,
        chat_session_id=chat_session_id,
    )

    history = []

    pending_question = None

    for message in messages:
        if message.role == "user":
            pending_question = message.content

        elif message.role == "assistant":
            history.append(
                {
                    "question": pending_question or "",
                    "answer": message.content,
                    "sources": message.sources or [],
                    "timestamp": message.created_at.isoformat(),
                }
            )

            pending_question = None

    return {
        "session_id": session_id,
        "history": history,
    }