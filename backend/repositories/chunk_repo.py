from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.models.db_models import Chunk


def create_chunk(
    db: Session,
    document_id: UUID,
    chunk_index: int,
    content: str,
    embedding: list[float] | None = None,
    page_number: int | None = None,
    section_title: str | None = None,
) -> Chunk:
    chunk = Chunk(
        document_id=document_id,
        chunk_index=chunk_index,
        page_number=page_number,
        section_title=section_title,
        content=content,
        embedding=embedding,
    )

    db.add(chunk)
    db.commit()
    db.refresh(chunk)

    return chunk


def list_document_chunks(
    db: Session,
    document_id: UUID,
) -> list[Chunk]:
    return (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index.asc())
        .all()
    )


def delete_document_chunks(
    db: Session,
    document_id: UUID,
) -> int:
    deleted = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .delete(synchronize_session=False)
    )

    db.commit()

    return deleted


def create_chunks_bulk(
    db: Session,
    document_id: UUID,
    chunks: list[dict],
    embeddings,
) -> list[Chunk]:
    chunk_rows = []

    for chunk, embedding in zip(
        chunks,
        embeddings,
    ):
        chunk_row = Chunk(
            document_id=document_id,
            chunk_index=chunk["chunk_index"],
            content=chunk["content"],
            page_number=chunk.get("page_number"),
            section_title=chunk.get("section_title"),
            embedding=embedding.tolist(),
        )

        chunk_rows.append(chunk_row)

    db.add_all(chunk_rows)
    db.commit()

    return chunk_rows

def search_similar_chunks(
    db: Session,
    document_id: UUID,
    query_embedding,
    top_k: int = 10,
) -> list[tuple[Chunk, float]]:
    """
    Find the most semantically similar chunks using
    pgvector cosine distance.
    """

    embedding_list = query_embedding.tolist()

    distance = Chunk.embedding.cosine_distance(
        embedding_list
    ).label("distance")

    statement = (
        select(
            Chunk,
            distance,
        )
        .where(
            Chunk.document_id == document_id,
            Chunk.embedding.is_not(None),
        )
        .order_by(distance)
        .limit(top_k)
    )

    rows = db.execute(statement).all()

    return [
        (chunk, float(distance_value))
        for chunk, distance_value in rows
    ]