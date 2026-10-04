"""Expand legacy document constraints and bind OAuth linking to a live session."""
from alembic import op

revision="0002_compatibility"
down_revision="0001_platform"
branch_labels=None
depends_on=None

def upgrade():
    op.execute("""
        ALTER TABLE documents DROP CONSTRAINT IF EXISTS chk_documents_file_type;
        ALTER TABLE documents DROP CONSTRAINT IF EXISTS chk_documents_status;
        ALTER TABLE documents ADD CONSTRAINT chk_documents_file_type CHECK (file_type IN ('pdf','docx','md','txt'));
        ALTER TABLE documents ADD CONSTRAINT chk_documents_status CHECK (status IN ('uploaded','queued','processing','indexed','failed'));
        ALTER TABLE oauth_attempts ADD COLUMN IF NOT EXISTS link_session_id UUID REFERENCES auth_sessions(id) ON DELETE CASCADE;
    """)

def downgrade():
    raise RuntimeError("Restore a backup to revert format support without invalidating existing content.")
