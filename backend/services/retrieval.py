from sqlalchemy import select, func, literal_column
from backend.models.db_models import Chunk, Document
from backend.services.embeddings import embed_texts
from backend.config import settings


def hybrid_search(db,document_ids,query,top_k=None):
    top_k=top_k or settings.RETRIEVAL_TOP_K
    vector=embed_texts([query])[0].tolist()
    scoped=select(Chunk,Document.filename).join(Document,Document.id==Chunk.document_id)\
        .where(Chunk.document_id.in_(document_ids),Chunk.embedding.is_not(None),Document.status=="indexed")
    semantic=db.execute(scoped.order_by(Chunk.embedding.cosine_distance(vector)).limit(top_k*2)).all()
    search_vector=func.to_tsvector(literal_column("'english'"),Chunk.content)
    search_query=func.plainto_tsquery(literal_column("'english'"),query)
    keyword=db.execute(scoped.where(search_vector.op("@@")(search_query))\
                       .order_by(func.ts_rank_cd(search_vector,search_query).desc()).limit(top_k*2)).all()
    fused={}
    for rows in (semantic,keyword):
        for rank,(chunk,filename) in enumerate(rows,1):
            candidate=fused.setdefault(chunk.id,{"chunk":chunk,"filename":filename,"score":0})
            candidate["score"]+=1/(60+rank)
    return sorted(fused.values(),key=lambda row:row["score"],reverse=True)[:top_k]
