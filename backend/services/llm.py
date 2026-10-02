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
   [Source: annual_report.pdf | Page 4 | Chunk 8]
   [Source: policy.docx | Section: Revenue | Chunk 12]
4. When you use information from a source, cite it in the answer.
5. Use concise citations such as:
   [annual_report.pdf, Page 4]
   [annual_report.pdf, Page 4, Chunk 8]
   [policy.docx, Section: Revenue]
6. Do not invent filenames, page numbers, sections, chunks, or citations.
7. Prefer filename + page number when a page number is available.
8. If multiple sources support the answer, cite the most relevant sources.
9. Use the source labels exactly as provided in the context.

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