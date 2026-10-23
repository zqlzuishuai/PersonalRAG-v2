-- PostgreSQL 18 + pgvector. One-time install into personalrag_v2 only.
-- psql -X -v ON_ERROR_STOP=1 -U postgres -d personalrag_v2 -f 01_schema.sql
\set ON_ERROR_STOP on
BEGIN;
DO $$ BEGIN
  IF current_database()<>'personalrag_v2' THEN
    RAISE EXCEPTION 'Wrong database: %. Expected personalrag_v2; old databases must not be modified',current_database();
  END IF;
  IF current_setting('server_version_num')::integer<180000 THEN
    RAISE EXCEPTION 'PostgreSQL 18 or newer is required';
  END IF;
  IF to_regnamespace('rag') IS NOT NULL THEN
    RAISE EXCEPTION 'Schema rag already exists; this is an initial install, not an upgrade or overwrite';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='personalrag_v2_owner')
     OR NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='personalrag_v2_app')
     OR NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='personalrag_v2_auth') THEN
    RAISE EXCEPTION 'Execute 00_create_database.sql first';
  END IF;
END $$;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO personalrag_v2_owner,personalrag_v2_app;
CREATE SCHEMA rag AUTHORIZATION personalrag_v2_owner;
SET LOCAL ROLE personalrag_v2_owner;
SET LOCAL search_path=rag,public,pg_catalog;

CREATE FUNCTION rag.current_user_id() RETURNS uuid
LANGUAGE sql STABLE PARALLEL SAFE SET search_path=pg_catalog AS
$$ SELECT nullif(current_setting('app.user_id',true),'')::uuid $$;
CREATE FUNCTION rag.text_sha256(value text) RETURNS text
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE SET search_path=pg_catalog AS
$$ SELECT encode(sha256(convert_to(value,'UTF8')),'hex') $$;
CREATE FUNCTION rag.json_sha256(value jsonb) RETURNS text
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE SET search_path=pg_catalog,rag AS
$$ SELECT rag.text_sha256(value::text) $$;
CREATE FUNCTION rag.safe_storage_key(value text) RETURNS boolean
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE SET search_path=pg_catalog AS
$$ SELECT length(value)>0 AND left(value,1)<>'/' AND position(chr(92) IN value)=0
   AND value !~ '(^|/)[.][.](/|$)' AND value !~ '^[A-Za-z]:' $$;

CREATE TABLE rag.users (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 login_name text NOT NULL UNIQUE CHECK(login_name=lower(btrim(login_name)) AND length(login_name) BETWEEN 1 AND 200),
 password_hash text NOT NULL CHECK(length(password_hash)>=20),
 mcp_token_hash text UNIQUE CHECK(mcp_token_hash ~ '^[0-9a-f]{64}$'),
 status text NOT NULL DEFAULT 'active' CHECK(status IN('active','disabled')),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE rag.folders (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES rag.users(id),
 parent_id uuid, name text NOT NULL CHECK(length(btrim(name)) BETWEEN 1 AND 200),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(user_id,id), UNIQUE NULLS NOT DISTINCT(user_id,parent_id,name),
 FOREIGN KEY(user_id,parent_id) REFERENCES rag.folders(user_id,id), CHECK(parent_id IS DISTINCT FROM id)
);
CREATE TABLE rag.documents (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES rag.users(id),
 folder_id uuid, title text NOT NULL CHECK(length(btrim(title))>0),
 source_type text NOT NULL CHECK(source_type IN('conversation','file','web')),
 source_key text NOT NULL CHECK(length(btrim(source_key))>0), tags text[] NOT NULL DEFAULT '{}',
 metadata jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(metadata)='object'),
 latest_version_id uuid, active_run_id uuid,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), deleted_at timestamptz,
 UNIQUE(user_id,id), UNIQUE(user_id,source_type,source_key),
 FOREIGN KEY(user_id,folder_id) REFERENCES rag.folders(user_id,id),
 CHECK(array_position(tags,NULL) IS NULL)
);
CREATE TABLE rag.document_versions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, document_id uuid NOT NULL,
 version_no integer NOT NULL CHECK(version_no>0),
 raw_sha256 text NOT NULL CHECK(raw_sha256 ~ '^[0-9a-f]{64}$'),
 storage_key text NOT NULL CHECK(rag.safe_storage_key(storage_key)),
 media_type text NOT NULL CHECK(length(btrim(media_type))>0), byte_size bigint NOT NULL CHECK(byte_size>=0),
 captured_at timestamptz NOT NULL DEFAULT now(), source_modified_at timestamptz,
 metadata jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(metadata)='object'), created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(user_id,document_id,id), UNIQUE(document_id,version_no),
 FOREIGN KEY(user_id,document_id) REFERENCES rag.documents(user_id,id)
);
CREATE TABLE rag.processing_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, document_id uuid NOT NULL, version_id uuid NOT NULL,
 config jsonb NOT NULL CHECK(jsonb_typeof(config)='object'
   AND config @> '{"embedding":{"dimensions":1024}}'::jsonb
   AND length(coalesce(config #>> '{embedding,model}',''))>0
   AND config ?& ARRAY['parser','chunker','embedding']),
 config_hash text GENERATED ALWAYS AS (rag.json_sha256(config)) STORED,
 status text NOT NULL DEFAULT 'queued' CHECK(status IN('queued','running','succeeded','failed','cancelled')),
 attempt_count integer NOT NULL DEFAULT 0 CHECK(attempt_count>=0), next_attempt_at timestamptz NOT NULL DEFAULT now(),
 worker_id text, lease_expires_at timestamptz, heartbeat_at timestamptz, started_at timestamptz, finished_at timestamptz,
 error_code text, error_summary text,
 parsed_storage_key text CHECK(rag.safe_storage_key(parsed_storage_key)),
 parsed_sha256 text CHECK(parsed_sha256 ~ '^[0-9a-f]{64}$'), chunk_count integer NOT NULL DEFAULT 0 CHECK(chunk_count>=0),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(user_id,document_id,id), UNIQUE(user_id,document_id,version_id,id), UNIQUE(version_id,config_hash),
 FOREIGN KEY(user_id,document_id,version_id) REFERENCES rag.document_versions(user_id,document_id,id),
 CHECK((status IN('succeeded','failed','cancelled'))=(finished_at IS NOT NULL)),
 CHECK(status<>'running' OR (worker_id IS NOT NULL AND lease_expires_at IS NOT NULL AND started_at IS NOT NULL)),
 CHECK(status<>'succeeded' OR (parsed_storage_key IS NOT NULL AND parsed_sha256 IS NOT NULL))
);
CREATE TABLE rag.chunks (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, document_id uuid NOT NULL,
 version_id uuid NOT NULL, run_id uuid NOT NULL, ordinal integer NOT NULL CHECK(ordinal>=0),
 content text NOT NULL CHECK(length(content)>0),
 content_sha256 text GENERATED ALWAYS AS (rag.text_sha256(content)) STORED,
 token_count integer CHECK(token_count>=0), embedding public.vector(1024) NOT NULL CHECK(public.vector_norm(embedding)>0),
 locator jsonb NOT NULL CHECK(jsonb_typeof(locator)='object'),
 metadata jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(metadata)='object'), created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(run_id,ordinal), UNIQUE(user_id,document_id,version_id,id),
 FOREIGN KEY(user_id,document_id,version_id,run_id) REFERENCES rag.processing_runs(user_id,document_id,version_id,id)
);
ALTER TABLE rag.documents ADD CONSTRAINT documents_latest_version_fk
 FOREIGN KEY(user_id,id,latest_version_id) REFERENCES rag.document_versions(user_id,document_id,id) DEFERRABLE;
ALTER TABLE rag.documents ADD CONSTRAINT documents_active_run_fk
 FOREIGN KEY(user_id,id,active_run_id) REFERENCES rag.processing_runs(user_id,document_id,id) DEFERRABLE;

CREATE TABLE rag.conversations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES rag.users(id), title text NOT NULL DEFAULT '',
 next_message_sequence bigint NOT NULL DEFAULT 1 CHECK(next_message_sequence>0),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), deleted_at timestamptz,
 UNIQUE(user_id,id)
);
CREATE TABLE rag.messages (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, conversation_id uuid NOT NULL,
 sequence bigint NOT NULL CHECK(sequence>0), role text NOT NULL CHECK(role IN('user','assistant')),
 content text NOT NULL DEFAULT '', status text NOT NULL DEFAULT 'pending'
   CHECK(status IN('pending','streaming','completed','failed','cancelled')),
 created_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz,
 UNIQUE(user_id,conversation_id,id), UNIQUE(user_id,id), UNIQUE(conversation_id,sequence),
 FOREIGN KEY(user_id,conversation_id) REFERENCES rag.conversations(user_id,id) ON DELETE CASCADE,
 CHECK(status<>'completed' OR completed_at IS NOT NULL), CHECK(role<>'user' OR status='completed')
);
CREATE TABLE rag.answer_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, conversation_id uuid NOT NULL,
 question_message_id uuid NOT NULL, answer_message_id uuid, client_request_id uuid NOT NULL,
 status text NOT NULL DEFAULT 'queued' CHECK(status IN('queued','running','succeeded','failed','cancelled')),
 retrieval_config jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(retrieval_config)='object'),
 model_config jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(model_config)='object'), retrieval_query text,
 context_snapshot jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(context_snapshot)='array'),
 usage jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(usage)='object'),
 started_at timestamptz, finished_at timestamptz, error_code text, error_summary text,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(user_id,client_request_id), UNIQUE(answer_message_id),
 FOREIGN KEY(user_id,conversation_id) REFERENCES rag.conversations(user_id,id) ON DELETE CASCADE,
 FOREIGN KEY(user_id,conversation_id,question_message_id) REFERENCES rag.messages(user_id,conversation_id,id),
 FOREIGN KEY(user_id,conversation_id,answer_message_id) REFERENCES rag.messages(user_id,conversation_id,id),
 CHECK(question_message_id IS DISTINCT FROM answer_message_id),
 CHECK((status IN('succeeded','failed','cancelled'))=(finished_at IS NOT NULL)),
 CHECK(status NOT IN('running','succeeded') OR started_at IS NOT NULL),
 CHECK(status<>'succeeded' OR answer_message_id IS NOT NULL)
);
CREATE TABLE rag.citations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL, answer_message_id uuid NOT NULL,
 citation_no integer NOT NULL CHECK(citation_no>0), document_id uuid, version_id uuid, chunk_id uuid,
 locator jsonb NOT NULL DEFAULT '{}' CHECK(jsonb_typeof(locator)='object'), quote text NOT NULL DEFAULT '',
 source_status text NOT NULL DEFAULT 'available' CHECK(source_status IN('available','deleted')),
 created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(answer_message_id,citation_no),
 FOREIGN KEY(user_id,answer_message_id) REFERENCES rag.messages(user_id,id) ON DELETE CASCADE,
 FOREIGN KEY(user_id,document_id,version_id,chunk_id) REFERENCES rag.chunks(user_id,document_id,version_id,id),
 CHECK((source_status='available' AND document_id IS NOT NULL AND version_id IS NOT NULL AND chunk_id IS NOT NULL AND length(quote)>0)
    OR (source_status='deleted' AND document_id IS NULL AND version_id IS NULL AND chunk_id IS NULL AND quote='' AND locator='{}'::jsonb))
);

-- Supporting indexes: tenant navigation, work claiming, references and retrieval.
CREATE INDEX documents_folder_idx ON rag.documents(user_id,folder_id);
CREATE INDEX documents_recent_idx ON rag.documents(user_id,updated_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX versions_storage_idx ON rag.document_versions(user_id,storage_key);
CREATE INDEX processing_queue_idx ON rag.processing_runs(user_id,next_attempt_at,created_at) WHERE status='queued';
CREATE INDEX processing_lease_idx ON rag.processing_runs(lease_expires_at) WHERE status='running';
CREATE INDEX processing_version_idx ON rag.processing_runs(user_id,document_id,version_id);
CREATE INDEX chunks_owner_run_idx ON rag.chunks(user_id,run_id);
CREATE INDEX chunks_version_idx ON rag.chunks(user_id,document_id,version_id);
CREATE INDEX chunks_embedding_hnsw ON rag.chunks USING hnsw(embedding public.vector_cosine_ops);
CREATE INDEX chunks_content_trgm ON rag.chunks USING gin(content public.gin_trgm_ops);
CREATE INDEX conversations_recent_idx ON rag.conversations(user_id,updated_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX messages_owner_conversation_idx ON rag.messages(user_id,conversation_id,sequence);
CREATE UNIQUE INDEX answer_one_running_per_conversation ON rag.answer_runs(conversation_id) WHERE status='running';
CREATE INDEX answer_question_idx ON rag.answer_runs(user_id,conversation_id,question_message_id,created_at DESC);
CREATE INDEX answer_conversation_idx ON rag.answer_runs(user_id,conversation_id);
CREATE INDEX citations_source_idx ON rag.citations(user_id,document_id,version_id,chunk_id);

-- Identity fields cannot be reassigned across users or parent entities.
CREATE FUNCTION rag.guard_identity() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,rag,public AS $$
DECLARE key text;
BEGIN
 FOREACH key IN ARRAY TG_ARGV LOOP
   IF (to_jsonb(NEW)->key) IS DISTINCT FROM (to_jsonb(OLD)->key) THEN
     RAISE EXCEPTION 'Immutable identity field %.%',TG_TABLE_NAME,key USING ERRCODE='23514';
   END IF;
 END LOOP;
 RETURN NEW;
END $$;
CREATE FUNCTION rag.touch_updated_at() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN NEW.updated_at=clock_timestamp(); RETURN NEW; END $$;
CREATE FUNCTION rag.reject_version_update() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 RAISE EXCEPTION 'Raw versions are immutable; insert a new version' USING ERRCODE='23514';
END $$;
CREATE TRIGGER versions_immutable BEFORE UPDATE ON rag.document_versions
 FOR EACH ROW EXECUTE FUNCTION rag.reject_version_update();

CREATE FUNCTION rag.guard_processing_run() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,rag,public AS $$
DECLARE actual_count bigint;
BEGIN
 IF TG_OP='INSERT' THEN
   IF NEW.status<>'queued' THEN RAISE EXCEPTION 'New processing run must be queued' USING ERRCODE='23514'; END IF;
   RETURN NEW;
 END IF;
 IF OLD.status='succeeded' THEN
   RAISE EXCEPTION 'Successful processing runs are immutable' USING ERRCODE='23514';
 END IF;
 IF NEW.config IS DISTINCT FROM OLD.config THEN
   RAISE EXCEPTION 'Processing config is immutable' USING ERRCODE='23514';
 END IF;
 IF NEW.status<>OLD.status AND NOT (
   (OLD.status='queued' AND NEW.status IN('running','cancelled')) OR
   (OLD.status='running' AND NEW.status IN('queued','succeeded','failed','cancelled')) OR
   (OLD.status IN('failed','cancelled') AND NEW.status='queued')) THEN
   RAISE EXCEPTION 'Invalid processing transition % -> %',OLD.status,NEW.status USING ERRCODE='23514';
 END IF;
 IF NEW.status='succeeded' THEN
   SELECT count(*) INTO actual_count FROM rag.chunks WHERE user_id=NEW.user_id AND run_id=NEW.id;
   IF actual_count<>NEW.chunk_count THEN
     RAISE EXCEPTION 'chunk_count does not match stored chunks' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER processing_state BEFORE INSERT OR UPDATE ON rag.processing_runs
 FOR EACH ROW EXECUTE FUNCTION rag.guard_processing_run();

CREATE FUNCTION rag.guard_chunk() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,rag,public AS $$
DECLARE parent_status text;
BEGIN
 IF TG_OP='UPDATE' THEN RAISE EXCEPTION 'Chunks are immutable; create another run' USING ERRCODE='23514'; END IF;
 IF TG_OP='DELETE' THEN
   IF EXISTS(SELECT 1 FROM rag.documents WHERE user_id=OLD.user_id AND active_run_id=OLD.run_id) THEN
     RAISE EXCEPTION 'Clear active_run_id before deleting published chunks' USING ERRCODE='23514';
   END IF;
   RETURN OLD;
 END IF;
 SELECT status INTO parent_status FROM rag.processing_runs
   WHERE user_id=NEW.user_id AND id=NEW.run_id FOR SHARE;
 IF parent_status IS DISTINCT FROM 'running' THEN
   RAISE EXCEPTION 'Chunks may be inserted only into a running task owned by this user' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER chunks_guard BEFORE INSERT OR UPDATE OR DELETE ON rag.chunks
 FOR EACH ROW EXECUTE FUNCTION rag.guard_chunk();

CREATE FUNCTION rag.guard_document_publication() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,rag,public AS $$
DECLARE run_status text; run_version uuid;
BEGIN
 IF TG_OP='INSERT' THEN
   IF NEW.latest_version_id IS NOT NULL OR NEW.active_run_id IS NOT NULL THEN
     RAISE EXCEPTION 'Create the document first, then attach versions and published results' USING ERRCODE='23514';
   END IF;
   RETURN NEW;
 END IF;
 IF NEW.active_run_id IS NOT NULL AND NEW.active_run_id IS DISTINCT FROM OLD.active_run_id THEN
   IF NEW.deleted_at IS NOT NULL THEN
     RAISE EXCEPTION 'Cannot publish a deleted document' USING ERRCODE='23514';
   END IF;
   SELECT status,version_id INTO run_status,run_version FROM rag.processing_runs
    WHERE user_id=NEW.user_id AND document_id=NEW.id AND id=NEW.active_run_id FOR SHARE;
   IF run_status IS DISTINCT FROM 'succeeded' OR run_version IS DISTINCT FROM NEW.latest_version_id THEN
     RAISE EXCEPTION 'Publish only a successful run of the latest version' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER documents_publication BEFORE INSERT OR UPDATE ON rag.documents
 FOR EACH ROW EXECUTE FUNCTION rag.guard_document_publication();

CREATE FUNCTION rag.guard_answer_links() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,rag,public AS $$
DECLARE message_role text; message_status text; question_sequence bigint; answer_sequence bigint;
BEGIN
 IF TG_OP='UPDATE' THEN
   IF OLD.status IN('succeeded','failed','cancelled') AND NEW.status IS DISTINCT FROM OLD.status THEN
     RAISE EXCEPTION 'Terminal answer runs cannot be restarted; create a new request' USING ERRCODE='23514';
   END IF;
   IF OLD.answer_message_id IS NOT NULL AND NEW.answer_message_id IS DISTINCT FROM OLD.answer_message_id THEN
     RAISE EXCEPTION 'An answer run cannot be repointed to another answer' USING ERRCODE='23514';
   END IF;
 END IF;
 SELECT role,status,sequence INTO message_role,message_status,question_sequence FROM rag.messages
   WHERE user_id=NEW.user_id AND conversation_id=NEW.conversation_id AND id=NEW.question_message_id;
 IF message_role IS DISTINCT FROM 'user' OR message_status IS DISTINCT FROM 'completed' THEN
   RAISE EXCEPTION 'Question must be a completed user message in this conversation' USING ERRCODE='23514';
 END IF;
 IF NEW.answer_message_id IS NOT NULL THEN
   SELECT role,status,sequence INTO message_role,message_status,answer_sequence FROM rag.messages
     WHERE user_id=NEW.user_id AND conversation_id=NEW.conversation_id AND id=NEW.answer_message_id;
   IF message_role IS DISTINCT FROM 'assistant' OR answer_sequence<=question_sequence
      OR (NEW.status='succeeded' AND message_status IS DISTINCT FROM 'completed') THEN
     RAISE EXCEPTION 'Answer must be an assistant message; successful answers must be completed' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER answer_links BEFORE INSERT OR UPDATE ON rag.answer_runs
 FOR EACH ROW EXECUTE FUNCTION rag.guard_answer_links();

CREATE FUNCTION rag.guard_completed_message() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF OLD.status='completed' AND (NEW.content IS DISTINCT FROM OLD.content
   OR NEW.status IS DISTINCT FROM OLD.status OR NEW.completed_at IS DISTINCT FROM OLD.completed_at) THEN
   RAISE EXCEPTION 'Completed messages are immutable; create another answer instead' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER completed_message_guard BEFORE UPDATE ON rag.messages
 FOR EACH ROW EXECUTE FUNCTION rag.guard_completed_message();

CREATE FUNCTION rag.guard_citation() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,rag,public AS $$
DECLARE message_role text; source_text text;
BEGIN
 SELECT role INTO message_role FROM rag.messages WHERE user_id=NEW.user_id AND id=NEW.answer_message_id;
 IF message_role IS DISTINCT FROM 'assistant' THEN
   RAISE EXCEPTION 'Citations belong to assistant messages' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND OLD.source_status='deleted' THEN
   RAISE EXCEPTION 'A deleted citation cannot be repointed to a different source' USING ERRCODE='23514';
 END IF;
 IF TG_OP='INSERT' AND NEW.source_status<>'available' THEN
   RAISE EXCEPTION 'New citations must refer to an available source' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND NEW.source_status='available' AND
    (NEW.document_id IS DISTINCT FROM OLD.document_id OR NEW.version_id IS DISTINCT FROM OLD.version_id
     OR NEW.chunk_id IS DISTINCT FROM OLD.chunk_id OR NEW.quote IS DISTINCT FROM OLD.quote
     OR NEW.locator IS DISTINCT FROM OLD.locator) THEN
   RAISE EXCEPTION 'Historical citations cannot be repointed or rewritten' USING ERRCODE='23514';
 END IF;
 IF NEW.source_status='available' THEN
   SELECT c.content INTO source_text FROM rag.chunks c
     JOIN rag.processing_runs r ON r.id=c.run_id AND r.user_id=c.user_id
     JOIN rag.documents d ON d.id=c.document_id AND d.user_id=c.user_id
     WHERE c.user_id=NEW.user_id AND c.id=NEW.chunk_id AND c.document_id=NEW.document_id
       AND c.version_id=NEW.version_id AND r.status='succeeded' AND d.deleted_at IS NULL FOR SHARE OF d;
   IF source_text IS NULL OR position(NEW.quote IN source_text)=0 THEN
     RAISE EXCEPTION 'Citation must quote an existing successful source owned by this user' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER citations_guard BEFORE INSERT OR UPDATE ON rag.citations
 FOR EACH ROW EXECUTE FUNCTION rag.guard_citation();

-- Attach generic identity/update triggers; explicit business references stay immutable.
DO $$
DECLARE t text; identity_fields text;
BEGIN
 FOR t,identity_fields IN SELECT * FROM (VALUES
 ('users', '''id'''), ('folders', '''id'',''user_id'''), ('documents', '''id'',''user_id'',''source_type'',''source_key'''),
 ('processing_runs', '''id'',''user_id'',''document_id'',''version_id'''),
 ('conversations', '''id'',''user_id'''), ('messages', '''id'',''user_id'',''conversation_id'',''sequence'',''role'''),
 ('answer_runs', '''id'',''user_id'',''conversation_id'',''question_message_id'',''client_request_id'''),
 ('citations', '''id'',''user_id'',''answer_message_id'',''citation_no''')) AS x(t,k) LOOP
   EXECUTE format('CREATE TRIGGER identity_guard BEFORE UPDATE ON rag.%I FOR EACH ROW EXECUTE FUNCTION rag.guard_identity(%s)',t,identity_fields);
 END LOOP;
 FOREACH t IN ARRAY ARRAY['users','folders','documents','processing_runs','conversations','answer_runs'] LOOP
   EXECUTE format('CREATE TRIGGER z_touch_updated_at BEFORE UPDATE ON rag.%I FOR EACH ROW EXECUTE FUNCTION rag.touch_updated_at()',t);
 END LOOP;
END $$;

-- All policies are tenant scoped. The authentication role can read only identities.
ALTER TABLE rag.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag.users FORCE ROW LEVEL SECURITY;
CREATE POLICY users_self ON rag.users TO personalrag_v2_app
 USING(id=rag.current_user_id()) WITH CHECK(id=rag.current_user_id());
CREATE POLICY users_auth_lookup ON rag.users FOR SELECT TO personalrag_v2_auth USING(true);
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['folders','documents','document_versions','processing_runs','chunks','conversations','messages','answer_runs','citations'] LOOP
   EXECUTE format('ALTER TABLE rag.%I ENABLE ROW LEVEL SECURITY',t);
   EXECUTE format('ALTER TABLE rag.%I FORCE ROW LEVEL SECURITY',t);
   EXECUTE format('CREATE POLICY tenant_scope ON rag.%I TO personalrag_v2_app USING(user_id=rag.current_user_id()) WITH CHECK(user_id=rag.current_user_id())',t);
 END LOOP;
END $$;

CREATE VIEW rag.searchable_chunks WITH(security_invoker=true) AS
 SELECT c.*,r.config_hash,r.config->'embedding' AS embedding_config
 FROM rag.chunks c JOIN rag.documents d ON d.user_id=c.user_id AND d.id=c.document_id AND d.active_run_id=c.run_id
 JOIN rag.processing_runs r ON r.user_id=c.user_id AND r.id=c.run_id
 WHERE d.deleted_at IS NULL AND r.status='succeeded';

REVOKE ALL ON ALL TABLES IN SCHEMA rag FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA rag FROM PUBLIC;
GRANT USAGE ON SCHEMA rag TO personalrag_v2_app,personalrag_v2_auth;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA rag TO personalrag_v2_app;
GRANT SELECT ON rag.users TO personalrag_v2_app;
GRANT UPDATE(password_hash,mcp_token_hash,updated_at) ON rag.users TO personalrag_v2_app;
GRANT SELECT(id,login_name,password_hash,mcp_token_hash,status) ON rag.users TO personalrag_v2_auth;
GRANT SELECT,INSERT,UPDATE,DELETE ON rag.folders,rag.documents,rag.processing_runs,rag.conversations,rag.messages,rag.answer_runs,rag.citations TO personalrag_v2_app;
GRANT SELECT,INSERT,DELETE ON rag.document_versions,rag.chunks TO personalrag_v2_app;
GRANT SELECT ON rag.searchable_chunks TO personalrag_v2_app;
ALTER DEFAULT PRIVILEGES FOR ROLE personalrag_v2_owner REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

COMMENT ON SCHEMA rag IS 'PersonalRAG v2: tenant-scoped document RAG, independently installed from the old database';
COMMENT ON TABLE rag.document_versions IS 'Immutable original file versions; files live outside PostgreSQL';
COMMENT ON TABLE rag.processing_runs IS 'Retryable processing task and immutable successful output configuration';
COMMENT ON TABLE rag.chunks IS 'Immutable chunks, one 1024-dimensional body embedding per chunk';
COMMENT ON VIEW rag.searchable_chunks IS 'Published non-deleted chunks only; caller must additionally filter the compatible embedding configuration';
COMMIT;
\echo 'Installed: 10 business tables in schema rag. No users or old data were imported.'
