-- Run with psql as PostgreSQL superuser. Creates only the new v2 database/roles.
-- No passwords are embedded; set LOGIN role passwords interactively afterwards.
\set ON_ERROR_STOP on
\connect postgres
DO $$
DECLARE role_name text;
BEGIN
  IF current_setting('server_version_num')::integer < 180000 THEN
    RAISE EXCEPTION 'PostgreSQL 18 or newer is required';
  END IF;
  IF NOT (SELECT rolsuper FROM pg_roles WHERE rolname=current_user) THEN
    RAISE EXCEPTION 'Execute bootstrap as a PostgreSQL superuser';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_database WHERE datname='personalrag_v2'
             AND datdba <> (SELECT oid FROM pg_roles WHERE rolname='personalrag_v2_owner'))
     OR EXISTS (SELECT 1 FROM pg_database WHERE datname='personalrag_v2')
        AND NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='personalrag_v2_owner') THEN
    RAISE EXCEPTION 'Existing personalrag_v2 has another owner; refusing to reuse it';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='personalrag_v2_owner') THEN
    CREATE ROLE personalrag_v2_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
  FOREACH role_name IN ARRAY ARRAY['personalrag_v2_app','personalrag_v2_auth'] LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname=role_name) THEN
      EXECUTE format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',role_name);
    END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN
      ('personalrag_v2_owner','personalrag_v2_app','personalrag_v2_auth')
      AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
     OR (SELECT rolcanlogin FROM pg_roles WHERE rolname='personalrag_v2_owner')
     OR EXISTS(SELECT 1 FROM pg_roles WHERE rolname IN('personalrag_v2_app','personalrag_v2_auth') AND NOT rolcanlogin) THEN
    RAISE EXCEPTION 'Existing v2 roles have unexpected privileges; refusing bootstrap';
  END IF;
  IF pg_has_role('personalrag_v2_app','personalrag_v2_owner','MEMBER')
     OR pg_has_role('personalrag_v2_auth','personalrag_v2_owner','MEMBER')
     OR pg_has_role('personalrag_v2_app','personalrag_v2_auth','MEMBER')
     OR pg_has_role('personalrag_v2_auth','personalrag_v2_app','MEMBER') THEN
    RAISE EXCEPTION 'v2 runtime roles must not inherit owner or authentication privileges';
  END IF;
END $$;
SELECT 'CREATE DATABASE personalrag_v2 OWNER personalrag_v2_owner TEMPLATE template0 ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname='personalrag_v2')
\gexec
REVOKE ALL ON DATABASE personalrag_v2 FROM PUBLIC;
GRANT CONNECT ON DATABASE personalrag_v2 TO personalrag_v2_app, personalrag_v2_auth;
ALTER ROLE personalrag_v2_app IN DATABASE personalrag_v2 SET search_path = rag, public;
ALTER ROLE personalrag_v2_auth IN DATABASE personalrag_v2 SET search_path = rag, pg_catalog;
ALTER ROLE personalrag_v2_auth IN DATABASE personalrag_v2 SET default_transaction_read_only = on;
\echo 'Database ready. Set passwords with: \password personalrag_v2_app and \password personalrag_v2_auth'
