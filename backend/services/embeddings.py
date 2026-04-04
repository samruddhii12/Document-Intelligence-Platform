from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

# Load once globally (important for performance)
model = SentenceTransformer("all-mpnet-base-v2")


def generate_embeddings(chunks: List[str]) -> np.ndarray:
    """
    Convert list of text chunks into embedding vectors.
    """
    if not chunks:
        return np.array([])

    embeddings = model.encode(
        chunks,
        convert_to_numpy=True,
        show_progress_bar=False
    )

    return embeddings