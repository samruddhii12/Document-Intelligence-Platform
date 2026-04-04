from typing import List
import tiktoken
import re


def split_into_paragraphs(text: str) -> List[str]:
    """
    Split text into logical paragraphs.
    """
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_single_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
    model_name: str = "gpt-3.5-turbo"
) -> List[str]:
    """
    Split one text block into token-aware overlapping chunks.
    """
    if not text.strip():
        return []

    encoder = tiktoken.encoding_for_model(model_name)
    tokens = encoder.encode(text)

    chunks = []
    start = 0
    total_tokens = len(tokens)

    while start < total_tokens:
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = encoder.decode(chunk_tokens).strip()

        if chunk_text:
            chunks.append(chunk_text)

        step = chunk_size - overlap
        if step <= 0:
            raise ValueError("chunk_size must be greater than overlap")

        start += step

    return chunks


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
    model_name: str = "gpt-3.5-turbo"
) -> List[str]:
    """
    Split text into paragraph-aware token chunks.
    """
    if not text.strip():
        return []

    paragraphs = split_into_paragraphs(text)

    final_chunks = []
    for para in paragraphs:
        para_chunks = chunk_single_text(
            para,
            chunk_size=chunk_size,
            overlap=overlap,
            model_name=model_name
        )
        final_chunks.extend(para_chunks)

    return final_chunks