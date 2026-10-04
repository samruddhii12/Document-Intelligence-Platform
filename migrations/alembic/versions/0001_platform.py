"""Baseline and additive upgrade from the existing document platform."""
from pathlib import Path
from datetime import timedelta
import hashlib
from alembic import op
import sqlalchemy as sa

revision = "0001_platform"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.exec_driver_sql(Path(__file__).with_name("0001_schema.sql").read_text())
    # Existing application tables are not replaced by CREATE TABLE IF NOT EXISTS.
    connection.exec_driver_sql("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE documents ALTER COLUMN storage_path DROP NOT NULL;
        ALTER TABLE documents ADD COLUMN IF NOT EXISTS object_id UUID REFERENCES stored_objects(id);
        ALTER TABLE documents ADD COLUMN IF NOT EXISTS error TEXT;
        ALTER TABLE documents ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;
        ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT;
        ALTER TABLE documents ADD COLUMN IF NOT EXISTS metadata_json JSONB;
        ALTER TABLE chunks ADD COLUMN IF NOT EXISTS location JSONB;
        ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS title VARCHAR(255);
        UPDATE chat_sessions SET title='New chat' WHERE title IS NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_object_id ON documents(object_id);
        CREATE INDEX IF NOT EXISTS ix_chunks_content_search ON chunks USING gin(to_tsvector('english', content));
    """)
    from backend.config import settings
    rows=connection.execute(sa.text("SELECT guest_id,min(created_at) AS created_at FROM workspaces WHERE guest_id IS NOT NULL GROUP BY guest_id")).mappings()
    for row in rows:
        existing=connection.execute(sa.text("SELECT 1 FROM guest_sessions WHERE token_hash=:token"), {"token": row["guest_id"]}).scalar()
        if existing:
            continue
        digest=hashlib.sha256(row["guest_id"].encode()).hexdigest()
        connection.execute(sa.text("INSERT INTO guest_sessions(token_hash,expires_at,claimed) VALUES (:token,:expiry,FALSE) ON CONFLICT DO NOTHING"),
                           {"token": digest, "expiry": row["created_at"]+timedelta(hours=settings.GUEST_TTL_HOURS)})
        connection.execute(sa.text("UPDATE workspaces SET guest_id=:digest WHERE guest_id=:raw"), {"digest":digest,"raw":row["guest_id"]})


def downgrade():
    raise RuntimeError("This migration preserves uploaded content and identities; restore a backup instead of dropping them.")
