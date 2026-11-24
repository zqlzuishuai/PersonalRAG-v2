-- Run as database administrator after 01_schema.sql.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL ROLE personalrag_v2_owner;

CREATE TABLE IF NOT EXISTS rag.mcp_access_identities (
    issuer text NOT NULL CHECK (btrim(issuer) <> ''),
    subject text NOT NULL CHECK (btrim(subject) <> ''),
    user_id uuid NOT NULL REFERENCES rag.users(id) ON DELETE CASCADE,
    PRIMARY KEY (issuer, subject)
);

RESET ROLE;
GRANT SELECT (issuer, subject, user_id) ON rag.mcp_access_identities TO personalrag_v2_auth;

COMMIT;
