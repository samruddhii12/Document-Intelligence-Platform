import requests
from fastapi import HTTPException
from backend.config import settings

def generate(prompt: str, temperature: float = 0.1) -> str:
    try:
        r=requests.post(settings.OLLAMA_URL,json={
            "model":settings.OLLAMA_MODEL,"prompt":prompt,"stream":False,
            "options":{"temperature":temperature}
        },timeout=(5,180))
        r.raise_for_status()
    except requests.Timeout as error:
        raise HTTPException(504,"Ollama timed out. Please try again.") from error
    except requests.ConnectionError as error:
        raise HTTPException(503,"Ollama is unavailable. Start it with 'ollama serve' and check OLLAMA_URL in .env.") from error
    except requests.HTTPError as error:
        if r.status_code == 404:
            raise HTTPException(503,f"Ollama model '{settings.OLLAMA_MODEL}' is unavailable. Install it with 'ollama pull {settings.OLLAMA_MODEL}'.") from error
        raise HTTPException(502,"Ollama could not generate a response. Check its server logs.") from error
    try:
        response=r.json()["response"].strip()
        if not response:
            raise ValueError("Empty response")
        return response
    except (ValueError,KeyError,AttributeError,TypeError) as error:
        raise HTTPException(502,"Ollama returned an invalid response. Please try again.") from error

def answer(context: str, question: str, memory: str="") -> str:
    return generate(f"""You are a grounded document intelligence assistant.
Use ONLY the supplied document context for factual claims. If the answer is not supported, say so.
Conversation context is only for resolving references; it is not evidence.

Conversation:
{memory}

Document context:
{context}

Question: {question}

Answer clearly and concisely.""")

def summarize(text: str) -> str:
    return generate(f"Summarize this document faithfully. Include purpose, key points, conclusions and important numbers.\n\n{text[:24000]}")

def suggested_questions(text: str) -> str:
    return generate(f"Return exactly 5 useful questions a reader could ask about this document, one per line.\n\n{text[:12000]}")
