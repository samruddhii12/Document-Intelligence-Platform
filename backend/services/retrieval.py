from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.models.db_models import Chunk, Document
from backend.services.embeddings import embed_texts

def hybrid_search(db: Session, document_ids, query: str, top_k=12):
    rows=(db.query(Chunk,Document.filename)
          .join(Document,Document.id==Chunk.document_id)
          .filter(Chunk.document_id.in_(document_ids),Chunk.embedding.is_not(None)).all())
    if not rows: return []
    qvec=embed_texts([query])[0].tolist()
    semantic=(db.execute(
        select(Chunk,Document.filename,Chunk.embedding.cosine_distance(qvec).label("d"))
        .join(Document,Document.id==Chunk.document_id)
        .where(Chunk.document_id.in_(document_ids),Chunk.embedding.is_not(None))
        .order_by("d").limit(top_k*2)
    ).all())
    tokens=[c.content.lower().split() for c,_ in rows]
    bm=BM25Okapi(tokens)
    scores=bm.get_scores(query.lower().split())
    keyword=sorted(zip(rows,scores),key=lambda x:x[1],reverse=True)[:top_k*2]
    fused={}
    for rank,(c,f,d) in enumerate(semantic,1):
        fused[c.id]={"chunk":c,"filename":f,"score":1/(60+rank)}
    for rank,((c,f),_) in enumerate(keyword,1):
        fused.setdefault(c.id,{"chunk":c,"filename":f,"score":0})
        fused[c.id]["score"]+=1/(60+rank)
    return sorted(fused.values(),key=lambda x:x["score"],reverse=True)[:top_k]
