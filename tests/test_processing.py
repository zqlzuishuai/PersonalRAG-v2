"""任务流程测试：模拟数据库/API，使用真实临时文件；不证明实际 PostgreSQL 行为。"""
import copy
import json
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import processing
from parsing import split_text


class TaskStore:
    def __init__(self):
        self.user, self.run, self.doc, self.version = [uuid4() for _ in range(4)]
        self.status, self.owner, self.active = "queued", None, None
        self.latest, self.chunks, self.deleted = self.version, [], False
        self.fail_insert = False
        self.lose_success_ack = False
        self.config = {
            "parser": {"encoding": "utf-8", "mime_type": "text/plain"},
            "chunker": {"type": "RecursiveTextSplitter", "chunk_size": 800, "chunk_overlap": 120},
            "embedding": {"provider": "aliyun", "model": "qwen3.7-text-embedding-flash", "dimensions": 1024},
        }

    @contextmanager
    def transaction(self, settings, user_id):
        old = copy.deepcopy(self.__dict__)
        self.visible = user_id == self.user
        try:
            yield self
        except BaseException:
            self.__dict__.update(old)
            raise
        if self.lose_success_ack and self.status == "succeeded":
            self.lose_success_ack = False
            raise ConnectionError("simulated commit acknowledgment loss")

    def execute(self, query, params):
        q = " ".join(query.lower().split())
        row = None
        if "set status = 'running'" in q:
            if self.visible and params[1] == self.run and self.status == "queued" and not self.deleted:
                self.owner, self.status = params[0], "running"
                row = (self.doc, self.version, self.config)
        elif q.startswith("select latest_version_id"):
            if self.visible and not self.deleted:
                row = (self.latest,)
        elif q.startswith("select id from rag.processing_runs"):
            if self.visible and self.status == "running" and params[1] == self.owner:
                row = (self.run,)
        elif q.startswith("insert into rag.chunks"):
            if self.fail_insert and len(self.chunks) == 1:
                raise RuntimeError("simulated SQL failure")
            self.chunks.append(params)
        elif "set status = 'succeeded'" in q:
            self.status = "succeeded"
        elif q.startswith("update rag.documents"):
            self.active = params[0]
        elif "set status = 'failed'" in q:
            if self.visible and self.status == "running" and params[-1] == self.owner:
                self.status = "failed"
        else:
            raise AssertionError(f"Unexpected SQL: {q}")
        return SimpleNamespace(fetchone=lambda: row)


class ProcessingTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = SimpleNamespace(raw_storage_dir=self.root)
        self.store = TaskStore()
        self.text = "用于验证任务切分、向量化和事务的中文原文。" * 100
        for name, value in (
            ("user_transaction", self.store.transaction),
            ("split_file", lambda *a, **kw: split_text(self.text)),
        ):
            p = patch.object(processing, name, value, create=True)
            p.start()
            self.addCleanup(p.stop)

    def execute(self):
        return processing.execute_processing_run(self.settings, self.store.user, self.store.run)

    def test_success_persists_configured_chunks_and_publishes(self):
        def embed(texts, config):
            self.assertEqual(self.store.status, "running")
            self.assertTrue(all(len(t) <= 800 for t in texts))
            return [[1.0] + [0.0] * 1023 for _ in texts]
        with patch.object(processing, "embed_texts", side_effect=embed, create=True):
            self.assertTrue(self.execute())
        self.assertEqual(self.store.status, "succeeded")
        self.assertEqual(self.store.active, self.store.run)
        self.assertGreater(len(self.store.chunks), 1)
        snapshots = list(self.root.rglob("*.json"))
        self.assertEqual(len(snapshots), 1)
        parsed = json.loads(snapshots[0].read_text(encoding="utf-8"))
        for ordinal, chunk in enumerate(self.store.chunks):
            content, locator = chunk[5], chunk[7].obj
            self.assertEqual(locator, {"type": "chunk", "ordinal": ordinal})
            self.assertEqual(parsed["chunks"][ordinal], content)

    def test_api_failure_marks_failed_without_partial_chunks(self):
        with patch.object(processing, "embed_texts", side_effect=RuntimeError("API failed"), create=True):
            with self.assertRaisesRegex(RuntimeError, "API failed"):
                self.execute()
        self.assertEqual(self.store.status, "failed")
        self.assertEqual(self.store.chunks, [])
        self.assertIsNone(self.store.active)

    def test_sql_failure_rolls_back_all_chunks_then_marks_failed(self):
        self.store.fail_insert = True
        with patch.object(processing, "embed_texts", side_effect=lambda ts, cfg: [[1.0] * 1024 for _ in ts], create=True):
            with self.assertRaisesRegex(RuntimeError, "SQL failure"):
                self.execute()
        self.assertEqual(self.store.status, "failed")
        self.assertEqual(self.store.chunks, [])
        self.assertIsNone(self.store.active)

    def test_mismatched_chunk_config_fails_before_api_call(self):
        self.store.config["chunker"].update(chunk_size=512, chunk_overlap=64)
        with patch.object(processing, "embed_texts", create=True) as api:
            with self.assertRaisesRegex(ValueError, "800.*120"):
                self.execute()
            api.assert_not_called()
        self.assertEqual(self.store.status, "failed")
        self.assertEqual(self.store.chunks, [])

    def test_unsupported_encoding_fails_before_api_call(self):
        self.store.config["parser"]["encoding"] = "gbk"
        with patch.object(processing, "embed_texts", create=True) as api:
            with self.assertRaisesRegex(ValueError, "UTF-8"):
                self.execute()
            api.assert_not_called()
        self.assertEqual(self.store.status, "failed")

    def test_uses_existing_split_file_interface(self):
        with patch.object(processing, "split_file", return_value=["一段原文"], create=True) as splitter:
            with patch.object(processing, "embed_texts", return_value=[[1.0] * 1024], create=True):
                self.assertTrue(self.execute())
            splitter.assert_called_once_with(self.settings, self.store.user, self.store.version)

    def test_running_task_is_not_claimed_twice(self):
        self.store.status = "running"
        with self.assertRaises(ValueError):
            self.execute()

    def test_uncertain_commit_does_not_delete_committed_snapshot_or_mark_failed(self):
        self.store.lose_success_ack = True
        with patch.object(processing, "embed_texts", side_effect=lambda ts, cfg: [[1.0] * 1024 for _ in ts], create=True):
            with self.assertRaisesRegex(ConnectionError, "acknowledgment loss"):
                self.execute()
        self.assertEqual(self.store.status, "succeeded")
        self.assertEqual(self.store.active, self.store.run)
        self.assertGreater(len(self.store.chunks), 0)
        self.assertEqual(len(list(self.root.rglob("*.json"))), 1)

    def test_other_user_cannot_claim_task(self):
        with self.assertRaises(ValueError):
            processing.execute_processing_run(self.settings, uuid4(), self.store.run)
        self.assertEqual(self.store.status, "queued")

    def test_newer_version_prevents_publication_but_keeps_completed_result(self):
        def embed(texts, config):
            self.store.latest = uuid4()
            return [[1.0] * 1024 for _ in texts]
        with patch.object(processing, "embed_texts", side_effect=embed, create=True):
            self.assertTrue(self.execute())
        self.assertEqual(self.store.status, "succeeded")
        self.assertIsNone(self.store.active)

    def test_deleted_during_processing_is_not_published(self):
        def embed(texts, config):
            self.store.deleted = True
            return [[1.0] * 1024 for _ in texts]
        with patch.object(processing, "embed_texts", side_effect=embed, create=True):
            with self.assertRaises(ValueError):
                self.execute()
        self.assertEqual(self.store.status, "failed")
        self.assertEqual(self.store.chunks, [])

    def test_empty_document_succeeds_without_calling_api(self):
        self.text = " \n\t "
        with patch.object(processing, "embed_texts", create=True) as api:
            self.assertTrue(self.execute())
            api.assert_not_called()
        self.assertEqual(self.store.status, "succeeded")
        self.assertEqual(self.store.chunks, [])


if __name__ == "__main__":
    unittest.main()
