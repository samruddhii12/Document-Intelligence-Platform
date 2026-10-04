from functools import lru_cache
import logging
from fastapi import HTTPException
from sentence_transformers import SentenceTransformer
from backend.config import settings

@lru_cache(maxsize=1)
def model():
    return SentenceTransformer(settings.EMBEDDING_MODEL)

def embed_texts(texts: list[str]):
    try:
        vectors=model().encode(texts, normalize_embeddings=True)
    except Exception as error:
        logging.getLogger(__name__).exception("Embedding model failed")
        raise HTTPException(503,"The embedding model could not load or encode text. Check the model installation and backend logs.") from error
    if vectors.ndim != 2 or vectors.shape[1] != 768:
        raise HTTPException(503,"The embedding model must produce 768 dimensions to match the database.")
    return vectors
