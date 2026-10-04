from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from backend.models.db_models import GuestSession, Workspace, RateLimit, VerificationChallenge, OAuthAttempt, MailOutbox


def cleanup(db):
    now=datetime.now(timezone.utc)
    expired=[row.token_hash for row in db.query(GuestSession).filter(GuestSession.expires_at<=now).with_for_update(skip_locked=True).all()]
    # PostgreSQL cascading FKs remove payloads, datasets/results, chats, chunks and jobs.
    db.query(Workspace).filter(Workspace.guest_id.in_(expired)).delete(synchronize_session=False)
    db.query(GuestSession).filter(GuestSession.token_hash.in_(expired)).delete(synchronize_session=False)
    db.query(RateLimit).filter(RateLimit.expires_at<=now).delete(synchronize_session=False)
    db.query(OAuthAttempt).filter(OAuthAttempt.expires_at<=now).delete(synchronize_session=False)
    db.query(VerificationChallenge).filter(VerificationChallenge.expires_at<=now).delete(synchronize_session=False)
    db.query(MailOutbox).filter(MailOutbox.created_at<now-timedelta(minutes=30),MailOutbox.status.in_(["queued","failed"]))\
        .update({"status":"expired","body":""},synchronize_session=False)
    db.commit()
