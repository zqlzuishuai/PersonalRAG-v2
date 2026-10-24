-- PersonalRAG v2: Chinese BM25 initialization.
-- Run as postgres after 01_schema.sql; requires server-side pg_textsearch/zhparser.
-- Re-running validates existing objects and never rebuilds or drops an index.
-- pg_textsearch must already be included in shared_preload_libraries (restart required).
-- Reference: https://github.com/timescale/pg_textsearch
-- Reference: https://github.com/amutu/zhparser
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';
SET LOCAL search_path = pg_catalog, public, rag;

DO $preflight$
BEGIN
    IF current_database() <> 'personalrag_v2' THEN
        RAISE EXCEPTION 'Expected database personalrag_v2, got %', current_database();
    END IF;
    IF NOT (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) THEN
        RAISE EXCEPTION 'Run this initialization as postgres (superuser), not the application role';
    END IF;
    IF to_regclass('rag.chunks') IS NULL THEN
        RAISE EXCEPTION 'rag.chunks is missing; run 01_schema.sql first';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_attribute
        WHERE attrelid = 'rag.chunks'::regclass AND attname = 'content'
          AND atttypid = 'text'::regtype AND attnum > 0 AND NOT attisdropped
    ) THEN
        RAISE EXCEPTION 'Expected rag.chunks.content of type text';
    END IF;
END
$preflight$;

-- These statements do not install OS packages or edit PostgreSQL server settings.
CREATE EXTENSION IF NOT EXISTS zhparser WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pg_textsearch WITH SCHEMA public;

DO $extensions$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_extension e
        JOIN pg_namespace n ON n.oid = e.extnamespace
        WHERE e.extname IN ('zhparser', 'pg_textsearch') AND n.nspname <> 'public'
    ) OR to_regprocedure('public.to_bm25query(text,text)') IS NULL
      OR NOT EXISTS (SELECT 1 FROM pg_am WHERE amname = 'bm25') THEN
        RAISE EXCEPTION 'Expected public zhparser/pg_textsearch with to_bm25query(text,text) and bm25 access method';
    END IF;
END
$extensions$;

-- Only create missing configurations. Never change an existing tokenizer under an index.
DO $configuration$
BEGIN
    IF to_regconfig('public.chinese') IS NULL THEN
        CREATE TEXT SEARCH CONFIGURATION public.chinese (PARSER = public.zhparser);
        ALTER TEXT SEARCH CONFIGURATION public.chinese
            ADD MAPPING FOR n, v, a, i, e, l WITH pg_catalog.simple;
    END IF;
END
$configuration$;

DO $validate_configuration$
DECLARE
    actual_parser oid;
    actual_aliases text[];
    dictionaries_match boolean;
BEGIN
    SELECT cfgparser INTO actual_parser
    FROM pg_ts_config WHERE oid = 'public.chinese'::regconfig;
    IF actual_parser IS DISTINCT FROM (
        SELECT p.oid FROM pg_ts_parser p
        JOIN pg_namespace n ON n.oid = p.prsnamespace
        WHERE n.nspname = 'public' AND p.prsname = 'zhparser'
    ) THEN
        RAISE EXCEPTION 'Existing public.chinese does not use public.zhparser; no changes made';
    END IF;

    SELECT array_agg(t.alias ORDER BY t.alias),
           bool_and(m.mapdict = 'pg_catalog.simple'::regdictionary AND m.mapseqno = 1)
    INTO actual_aliases, dictionaries_match
    FROM pg_ts_config_map m
    JOIN LATERAL ts_token_type(actual_parser) t ON t.tokid = m.maptokentype
    WHERE m.mapcfg = 'public.chinese'::regconfig;
    IF actual_aliases IS DISTINCT FROM ARRAY['a','e','i','l','n','v']::text[]
       OR dictionaries_match IS DISTINCT FROM true THEN
        RAISE EXCEPTION 'Existing public.chinese mappings differ from n/v/a/i/e/l -> simple; inspect before migrating';
    END IF;
END
$validate_configuration$;

CREATE INDEX IF NOT EXISTS chunks_content_bm25
    ON rag.chunks USING bm25 (content)
    WITH (text_config = 'public.chinese');

-- IF NOT EXISTS alone does not establish that a same-named index has the right definition.
DO $validate_index$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_index i
        JOIN pg_class idx ON idx.oid = i.indexrelid
        JOIN pg_am am ON am.oid = idx.relam
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attname = 'content'
        WHERE i.indexrelid = 'rag.chunks_content_bm25'::regclass
          AND i.indrelid = 'rag.chunks'::regclass AND am.amname = 'bm25'
          AND i.indisvalid AND i.indisready AND i.indislive
          AND i.indnatts = 1 AND i.indnkeyatts = 1 AND i.indkey[0] = a.attnum
          AND i.indexprs IS NULL AND i.indpred IS NULL
          AND idx.reloptions @> ARRAY['text_config=public.chinese']::text[]
    ) THEN
        RAISE EXCEPTION 'Existing rag.chunks_content_bm25 has an incompatible or invalid definition; no automatic replacement';
    END IF;
END
$validate_index$;

COMMIT;

-- Read-only verification: no test users, documents, or chunks are inserted.
SELECT e.extname, e.extversion, n.nspname AS extension_schema
FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace
WHERE e.extname IN ('zhparser', 'pg_textsearch') ORDER BY e.extname;

SELECT alias, lexemes
FROM ts_debug('public.chinese', '四足机器人步态运动控制系统 RAG PostgreSQL 2026')
WHERE lexemes IS NOT NULL;

SELECT pg_get_indexdef('rag.chunks_content_bm25'::regclass) AS index_definition;
SELECT 'PASS: Chinese BM25 objects match the expected configuration' AS result;