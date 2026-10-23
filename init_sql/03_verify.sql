-- PostgreSQL 18 / psql. All fixtures are rolled back, including on assertion failure.
\set ON_ERROR_STOP on
BEGIN;
DO $$
BEGIN
  IF current_database() <> 'personalrag_v2' THEN
    RAISE EXCEPTION 'Run verification against personalrag_v2, not %', current_database();
  END IF;
  IF to_regclass('rag.users') IS NULL THEN
    RAISE EXCEPTION 'Schema missing: execute 01_schema.sql first';
  END IF;
  IF (SELECT count(*) FROM pg_tables WHERE schemaname = 'rag') <> 10 THEN
    RAISE EXCEPTION 'Expected exactly 10 core tables';
  END IF;
END $$;

CREATE FUNCTION pg_temp.assert_true(ok boolean, label text) RETURNS void
LANGUAGE plpgsql AS $$ BEGIN
  IF ok IS DISTINCT FROM true THEN RAISE EXCEPTION 'FAILED: %', label; END IF;
END $$;
CREATE FUNCTION pg_temp.expect_error(statement text, expected_state text) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE caught boolean := false;
BEGIN
  BEGIN EXECUTE statement;
  EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE <> expected_state THEN
      RAISE EXCEPTION 'Expected %, got %: %', expected_state, SQLSTATE, SQLERRM;
    END IF;
    caught := true;
  END;
  IF NOT caught THEN RAISE EXCEPTION 'Expected SQLSTATE %: %', expected_state, statement; END IF;
END $$;

INSERT INTO rag.users (id, login_name, password_hash) VALUES
 ('00000000-0000-4000-8000-000000000001', '__v2_verify_a__', 'verification-only-not-a-real-password-hash'),
 ('00000000-0000-4000-8000-000000000002', '__v2_verify_b__', 'verification-only-not-a-real-password-hash');

SET LOCAL ROLE personalrag_v2_app;
SELECT pg_temp.assert_true((SELECT count(*) = 0 FROM rag.users), 'no user context means no visible users');
SELECT set_config('app.user_id', '00000000-0000-4000-8000-000000000001', true);
SELECT pg_temp.assert_true((SELECT count(*) = 1 FROM rag.users), 'only current user visible');
SELECT pg_temp.expect_error($q$INSERT INTO rag.folders(user_id,name) VALUES
 ('00000000-0000-4000-8000-000000000002','forbidden')$q$, '42501');

INSERT INTO rag.folders(id,user_id,name) VALUES
 ('10000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001','notes');
SELECT pg_temp.expect_error($q$INSERT INTO rag.folders(user_id,name) VALUES
 ('00000000-0000-4000-8000-000000000001','notes')$q$, '23505');

INSERT INTO rag.documents(id,user_id,title,source_type,source_key) VALUES
 ('20000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001','fixture','file','verify-a');
INSERT INTO rag.document_versions(id,user_id,document_id,version_no,raw_sha256,storage_key,media_type,byte_size) VALUES
 ('30000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001',1,repeat('a',64),'raw/a.txt','text/plain',5),
 ('30000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001',2,repeat('b',64),'raw/b.txt','text/plain',5),
 ('30000000-0000-4000-8000-000000000003','00000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001',3,repeat('a',64),'raw/a.txt','text/plain',5);
SELECT pg_temp.assert_true((SELECT count(*)=3 FROM rag.document_versions), 'A-B-A keeps three versions');
SELECT pg_temp.expect_error($q$UPDATE rag.document_versions SET byte_size=6
 WHERE id='30000000-0000-4000-8000-000000000001'$q$, '42501');
INSERT INTO rag.documents(id,user_id,title,source_type,source_key) VALUES
 ('20000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000001','second fixture','file','verify-a-2');
SELECT pg_temp.expect_error($q$UPDATE rag.documents SET latest_version_id='30000000-0000-4000-8000-000000000001'
 WHERE id='20000000-0000-4000-8000-000000000002'$q$, '23503');
UPDATE rag.documents SET latest_version_id='30000000-0000-4000-8000-000000000003'
 WHERE id='20000000-0000-4000-8000-000000000001';

INSERT INTO rag.processing_runs(id,user_id,document_id,version_id,config) VALUES
 ('40000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001','30000000-0000-4000-8000-000000000003',
 '{"parser":{"name":"text","version":"1"},"chunker":{"name":"characters","size":1000},"embedding":{"provider":"dashscope","model":"fixture-model","dimensions":1024,"endpoint_type":"native","input_template":"detail_content:","normalize":true,"tokenizer":"fixture"}}');
SELECT pg_temp.expect_error($q$INSERT INTO rag.processing_runs(user_id,document_id,version_id,config)
 SELECT user_id,document_id,version_id,config FROM rag.processing_runs WHERE id='40000000-0000-4000-8000-000000000001'$q$, '23505');
SELECT pg_temp.expect_error($q$UPDATE rag.documents SET active_run_id='40000000-0000-4000-8000-000000000001'
 WHERE id='20000000-0000-4000-8000-000000000001'$q$, '23514');
UPDATE rag.processing_runs SET status='running',worker_id='verify',attempt_count=1,
 started_at=now(),heartbeat_at=now(),lease_expires_at=now()+interval '1 minute'
 WHERE id='40000000-0000-4000-8000-000000000001';
INSERT INTO rag.chunks(id,user_id,document_id,version_id,run_id,ordinal,content,embedding,locator) VALUES
 ('50000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001','20000000-0000-4000-8000-000000000001','30000000-0000-4000-8000-000000000003','40000000-0000-4000-8000-000000000001',0,
 'hello source', ('[' || array_to_string(array_prepend(1.0::real,array_fill(0.0::real,ARRAY[1023])),',') || ']')::public.vector,
 '{"spans":[{"kind":"text","start":0,"end":12}]}');
SELECT pg_temp.assert_true((SELECT count(*)=0 FROM rag.searchable_chunks), 'unpublished chunks are not searchable');
UPDATE rag.processing_runs SET status='succeeded',chunk_count=1,parsed_storage_key='parsed/a.json',
 parsed_sha256=repeat('c',64),finished_at=now(),worker_id=NULL,lease_expires_at=NULL
 WHERE id='40000000-0000-4000-8000-000000000001';
UPDATE rag.documents SET active_run_id='40000000-0000-4000-8000-000000000001'
 WHERE id='20000000-0000-4000-8000-000000000001';
SELECT pg_temp.assert_true((SELECT count(*)=1 FROM rag.searchable_chunks), 'published chunks searchable');
UPDATE rag.documents SET active_run_id=NULL,latest_version_id='30000000-0000-4000-8000-000000000002'
 WHERE id='20000000-0000-4000-8000-000000000001';
SELECT pg_temp.expect_error($q$UPDATE rag.documents SET active_run_id='40000000-0000-4000-8000-000000000001'
 WHERE id='20000000-0000-4000-8000-000000000001'$q$, '23514');
UPDATE rag.documents SET latest_version_id='30000000-0000-4000-8000-000000000003',active_run_id='40000000-0000-4000-8000-000000000001'
 WHERE id='20000000-0000-4000-8000-000000000001';
SELECT pg_temp.expect_error($q$UPDATE rag.processing_runs SET chunk_count=2
 WHERE id='40000000-0000-4000-8000-000000000001'$q$, '23514');
SELECT pg_temp.expect_error($q$DELETE FROM rag.chunks WHERE id='50000000-0000-4000-8000-000000000001'$q$, '23514');

INSERT INTO rag.conversations(id,user_id,title) VALUES
 ('60000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001','verify');
INSERT INTO rag.messages(id,user_id,conversation_id,sequence,role,content,status,completed_at) VALUES
 ('70000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001','60000000-0000-4000-8000-000000000001',1,'user','question','completed',now()),
 ('70000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000001','60000000-0000-4000-8000-000000000001',2,'assistant','answer [1]','completed',now());
INSERT INTO rag.answer_runs(id,user_id,conversation_id,question_message_id,client_request_id,status,started_at) VALUES
 ('80000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000001','60000000-0000-4000-8000-000000000001','70000000-0000-4000-8000-000000000001','90000000-0000-4000-8000-000000000001','running',now());
SELECT pg_temp.expect_error($q$INSERT INTO rag.answer_runs(user_id,conversation_id,question_message_id,client_request_id,status,started_at) VALUES
 ('00000000-0000-4000-8000-000000000001','60000000-0000-4000-8000-000000000001','70000000-0000-4000-8000-000000000001',gen_random_uuid(),'running',now())$q$, '23505');
UPDATE rag.answer_runs SET status='succeeded',answer_message_id='70000000-0000-4000-8000-000000000002',finished_at=now()
 WHERE id='80000000-0000-4000-8000-000000000001';
SELECT pg_temp.expect_error($q$UPDATE rag.messages SET content='rewritten answer'
 WHERE id='70000000-0000-4000-8000-000000000002'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE rag.answer_runs SET status='running',finished_at=NULL
 WHERE id='80000000-0000-4000-8000-000000000001'$q$, '23514');
INSERT INTO rag.citations(user_id,answer_message_id,citation_no,document_id,version_id,chunk_id,locator,quote) VALUES
 ('00000000-0000-4000-8000-000000000001','70000000-0000-4000-8000-000000000002',1,'20000000-0000-4000-8000-000000000001','30000000-0000-4000-8000-000000000003','50000000-0000-4000-8000-000000000001','{"spans":[]}','hello');
SELECT pg_temp.expect_error($q$UPDATE rag.citations SET quote='source' WHERE citation_no=1$q$, '23514');
UPDATE rag.documents SET deleted_at=now() WHERE id='20000000-0000-4000-8000-000000000001';
SELECT pg_temp.assert_true((SELECT count(*)=0 FROM rag.searchable_chunks), 'soft delete excludes chunks');
SELECT pg_temp.assert_true((SELECT count(*)=1 FROM rag.citations), 'soft delete preserves historical citation');

SELECT set_config('app.user_id', '00000000-0000-4000-8000-000000000002', true);
SELECT pg_temp.assert_true((SELECT count(*)=0 FROM rag.documents), 'second user cannot read first user documents');
SELECT pg_temp.assert_true((SELECT count(*)=0 FROM rag.citations), 'second user cannot read first user citations');
SELECT pg_temp.expect_error($q$INSERT INTO rag.documents(user_id,folder_id,title,source_type,source_key) VALUES
 ('00000000-0000-4000-8000-000000000002','10000000-0000-4000-8000-000000000001','cross-owner','file','bad')$q$, '23503');

RESET ROLE;
SET LOCAL ROLE personalrag_v2_auth;
SELECT pg_temp.assert_true((SELECT count(*)=2 FROM rag.users WHERE login_name LIKE '__v2_verify_%'), 'authentication can locate login identities');
SELECT pg_temp.expect_error('SELECT * FROM rag.documents', '42501');
SELECT pg_temp.expect_error($q$UPDATE rag.users SET status='disabled'$q$, '42501');
RESET ROLE;
ROLLBACK;
\echo 'PASS: schema, RLS, tenant FKs, versions, publication, citations, auth separation; fixtures rolled back.'
