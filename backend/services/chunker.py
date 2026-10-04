from backend.config import settings

def chunk_segments(segments):
    chunks=[]; idx=0
    size=settings.CHUNK_SIZE; overlap=settings.CHUNK_OVERLAP
    for seg in segments:
        text=seg["content"]
        start=0
        while start < len(text):
            part=text[start:start+size].strip()
            if part:
                chunks.append({**seg,"content":part,"chunk_index":idx}); idx+=1
            if start+size >= len(text): break
            start += max(1,size-overlap)
    return chunks
