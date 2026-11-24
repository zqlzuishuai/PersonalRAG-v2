-- Run as database administrator before deploying MCP write tools.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '5s';

ALTER TABLE rag.users
    ADD COLUMN mcp_write_enabled boolean NOT NULL DEFAULT false;

GRANT SELECT (mcp_write_enabled) ON rag.users TO personalrag_v2_auth;
COMMIT;
