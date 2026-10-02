import requests

# OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL_NAME = "tinyllama"  # Use small model for low RAM systems
from backend.config import OLLAMA_URL, OLLAMA_MODEL


import requests

from backend.config import OLLAMA_URL, OLLAMA_MODEL


def generate_answer(context: str, question: str) -> str:
    prompt = f"""
You are a document question-answering assistant.

Answer the user's question ONLY using the provided context.

Rules:
1. Do not use outside knowledge.
2. If the answer is not supported by the context, say:
   "I could not find enough information in the document to answer this."
3. The context may contain source labels such as:
   [Source: Page 4 | Chunk 8]
   [Source: Section: Revenue | Chunk 12]
4. When you use information from a source, cite it in the answer.
5. Use concise citations such as:
   [Page 4]
   [Page 4, Chunk 8]
   [Section: Revenue]
6. Do not invent page numbers, sections, chunks, or citations.
7. Prefer the page number when it is available.
8. If multiple sources support the answer, cite the most relevant sources.

Context:
{context}

Question:
{question}

Answer:
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
    )

    if response.status_code != 200:
        raise Exception(
            f"Ollama error: {response.text}"
        )

    result = response.json()

    return result.get("response", "").strip()