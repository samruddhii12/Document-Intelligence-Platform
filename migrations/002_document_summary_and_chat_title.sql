ALTER TABLE chat_sessions
    ADD COLUMN IF NOT EXISTS title VARCHAR(255);

UPDATE chat_sessions SET title = 'New chat' WHERE title IS NULL;

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS summary TEXT,
    ADD COLUMN IF NOT EXISTS metadata_json JSONB;
