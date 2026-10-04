"""Simple reproducible evaluation scaffold.
Populate questions.json with real questions/expected evidence from your corpus.
Never report improvement percentages unless produced from an actual run.
"""
import json, sys
from pathlib import Path

def term_recall(answer, terms):
    if not terms: return None
    a=answer.lower()
    return sum(t.lower() in a for t in terms)/len(terms)

if __name__=="__main__":
    path=Path(sys.argv[1] if len(sys.argv)>1 else "eval/questions.example.json")
    rows=json.loads(path.read_text())
    print(f"Loaded {len(rows)} evaluation cases.")
    print("Use these cases against /chats/{chat_id}/ask and record groundedness, citation correctness and expected-term recall.")
