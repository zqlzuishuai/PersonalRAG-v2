-- Run as database administrator. Tenant RLS is deliberately unchanged.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '5s';
GRANT INSERT(id,login_name,password_hash) ON rag.users TO personalrag_v2_app;
COMMIT;
