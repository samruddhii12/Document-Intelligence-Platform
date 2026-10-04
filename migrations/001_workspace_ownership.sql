-- ============================================================================
-- Migration 001 - Phase 3.2: Workspace ownership (user OR guest)
--
-- Run once against your PostgreSQL database, e.g.:
--     psql "$DATABASE_URL" -f migrations/001_workspace_ownership.sql
--
-- Safe to re-run (idempotent) and does NOT delete or modify existing rows.
--
-- Result:
--   workspaces.user_id   UUID        NULL  -> users(id), ON DELETE CASCADE
--   workspaces.guest_id  VARCHAR(64) NULL
--   exactly-one-owner rule enforced for every NEW or UPDATED workspace.
--   Pre-existing workspaces (no owner) are preserved.
-- ============================================================================

BEGIN;

-- 1. Owner columns (both nullable) ------------------------------------------
ALTER TABLE workspaces
    ADD COLUMN IF NOT EXISTS user_id UUID
        REFERENCES users (id) ON DELETE CASCADE;

ALTER TABLE workspaces
    ADD COLUMN IF NOT EXISTS guest_id VARCHAR(64);

-- If user_id already existed as NOT NULL (e.g. created from an earlier
-- version of the model), relax it so guests are possible.
ALTER TABLE workspaces
    ALTER COLUMN user_id DROP NOT NULL;

-- 2. Indexes -----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_workspaces_user_id
    ON workspaces (user_id);

CREATE INDEX IF NOT EXISTS ix_workspaces_guest_id
    ON workspaces (guest_id);

-- 3. Exactly-one-owner rule ---------------------------------------------------
-- NOT VALID: the rule is enforced for new/updated rows, but existing
-- ownerless workspaces from Phases 1-2 are not rejected.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_workspaces_single_owner'
          AND conrelid = 'workspaces'::regclass
    ) THEN
        ALTER TABLE workspaces
            ADD CONSTRAINT chk_workspaces_single_owner
            CHECK ((user_id IS NOT NULL) <> (guest_id IS NOT NULL))
            NOT VALID;
    END IF;
END
$$;

COMMIT;

-- ============================================================================
-- OPTIONAL: adopt pre-existing (ownerless) workspaces
--
-- Existing workspaces from Phases 1-2 have no owner. Once ownership checks
-- are added (Phase 3.7) nobody could open them. Pick ONE option.
--
-- Option A - give them to a development user (create one first):
--
--   UPDATE workspaces
--   SET user_id = '<DEV_USER_UUID>'
--   WHERE user_id IS NULL AND guest_id IS NULL;
--
-- Once EVERY workspace has an owner you can make the rule fully strict:
--
--   ALTER TABLE workspaces VALIDATE CONSTRAINT chk_workspaces_single_owner;
--
-- Option B - delete test data you no longer need (cascades to documents,
-- chunks, chat sessions and messages):
--
--   DELETE FROM workspaces WHERE user_id IS NULL AND guest_id IS NULL;
-- ============================================================================

-- Verify:
--   SELECT column_name, data_type, is_nullable
--   FROM information_schema.columns
--   WHERE table_name = 'workspaces'
--   ORDER BY ordinal_position;
--
--   SELECT conname, convalidated
--   FROM pg_constraint
--   WHERE conrelid = 'workspaces'::regclass;
