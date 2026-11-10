-- PersonalRAG v2: folder trash state and deletion batches.
-- One-time migration after 01_schema.sql. Run as an administrator able to SET ROLE.
-- psql -X -v ON_ERROR_STOP=1 -d personalrag_v2 -f 04_folder_trash.sql
\set ON_ERROR_STOP on

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL search_path = pg_catalog;

DO $preflight$
BEGIN
    IF current_database() <> 'personalrag_v2' THEN
        RAISE EXCEPTION 'Expected database personalrag_v2, got %', current_database();
    END IF;
    IF to_regclass('rag.folders') IS NULL OR to_regclass('rag.documents') IS NULL THEN
        RAISE EXCEPTION 'Base schema missing: run 01_schema.sql first';
    END IF;
END
$preflight$;

SET LOCAL ROLE personalrag_v2_owner;

ALTER TABLE rag.folders
    ADD COLUMN deleted_at timestamptz,
    ADD COLUMN trash_batch_id uuid,
    ADD CONSTRAINT folders_trash_state_ck
        CHECK ((deleted_at IS NULL) = (trash_batch_id IS NULL));

ALTER TABLE rag.documents
    ADD COLUMN trash_batch_id uuid,
    ADD CONSTRAINT documents_trash_batch_ck
        CHECK (trash_batch_id IS NULL OR deleted_at IS NOT NULL);

COMMENT ON COLUMN rag.folders.trash_batch_id IS
    'UUID shared by the folders and documents moved to trash in one subtree operation.';
COMMENT ON COLUMN rag.documents.trash_batch_id IS
    'Subtree trash batch UUID. NULL for active documents and individually trashed documents.';

COMMIT;
