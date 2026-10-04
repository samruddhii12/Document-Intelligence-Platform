from datetime import datetime, timedelta, timezone
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import case
from fastapi import HTTPException
from backend.models.db_models import RateLimit
from backend.security import token_hash


def limit(db, category, subject, maximum=10, seconds=3600):
    now=datetime.now(timezone.utc)
    statement=insert(RateLimit).values(key=category+":"+token_hash(subject),count=1,expires_at=now+timedelta(seconds=seconds))
    statement=statement.on_conflict_do_update(index_elements=[RateLimit.key],set_={
        "count":case((RateLimit.expires_at<=now,1),else_=RateLimit.count+1),
        "expires_at":case((RateLimit.expires_at<=now,now+timedelta(seconds=seconds)),else_=RateLimit.expires_at),
    }).returning(RateLimit.count)
    count=db.scalar(statement)
    db.commit()
    if count>maximum:
        raise HTTPException(429,"Too many requests. Please try again later.",headers={"Retry-After":str(seconds)})
