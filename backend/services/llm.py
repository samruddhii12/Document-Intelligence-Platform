import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"  # Use small model for low RAM systems


def generate_answer(context: str, question: str) -> str:
    prompt = f"""
You are a helpful assistant. Answer the question ONLY using the context below.

Context:
{context}

Question:

{question}

Answer:
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }
    )

    if response.status_code != 200:
        raise Exception(f"Ollama error: {response.text}")

    result = response.json()
    return result.get("response", "").strip()
