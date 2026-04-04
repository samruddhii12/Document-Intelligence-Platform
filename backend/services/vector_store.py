import faiss
import numpy as np
from sentence_transformers import CrossEncoder

# Load once globally
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def create_faiss_index(embeddings: np.ndarray):
    """
    Create FAISS index from embeddings.
    """
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings.astype("float32"))
    return index


def save_faiss_index(index, path: str):
    faiss.write_index(index, path)


def load_faiss_index(path: str):
    return faiss.read_index(path)


def search_index(index, query_embedding: np.ndarray, top_k: int = 10):
    """
    Search FAISS index and return top_k similar chunk indices.
    """
    query_embedding = query_embedding.astype("float32")
    distances, indices = index.search(query_embedding, top_k)
    return distances, indices


def rerank_chunks(query: str, retrieved_chunks: list[str], top_n: int = 5) -> list[str]:
    """
    Rerank retrieved chunks using a cross-encoder model.
    """
    if not retrieved_chunks:
        return []

    pairs = [[query, chunk] for chunk in retrieved_chunks]
    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(retrieved_chunks, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return [chunk for chunk, _ in ranked[:top_n]]