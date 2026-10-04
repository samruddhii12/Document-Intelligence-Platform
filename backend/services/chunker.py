from backend.config import settings
CHUNKER_VERSION="token-structure-v1"

def chunk_segments(segments,tokenizer=None):
    chunks=[]
    for seg in segments:
        text=seg["content"]
        if tokenizer:
            offsets=tokenizer(text,return_offsets_mapping=True,add_special_tokens=False,truncation=False)["offset_mapping"]
            size=min(settings.CHUNK_SIZE,max(16,min(tokenizer.model_max_length,384)-16))
            overlap=min(max(0,settings.CHUNK_OVERLAP),size-1)
            ranges=[(offsets[start][0],offsets[min(start+size,len(offsets))-1][1]) for start in range(0,len(offsets),size-overlap)]
        else:
            size=max(32,settings.CHUNK_SIZE); overlap=min(max(0,settings.CHUNK_OVERLAP),size-1)
            ranges=[(start,min(start+size,len(text))) for start in range(0,len(text),size-overlap)]
        for start,end in ranges:
            content=text[start:end].strip()
            if content:
                location={**seg.get("location",{}),"char_start":start,"char_end":end}
                chunks.append({**seg,"content":content,"chunk_index":len(chunks),"location":location})
            if end>=len(text): break
    return chunks
