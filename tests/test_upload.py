import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import documents
from config import Settings
from psycopg.errors import CheckViolation, OperationalError
from tests.fakes import Store


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = Settings(
            app_database_url="unused",
            auth_database_url="unused",
            raw_storage_dir=self.root / "raw",
            embedding_provider="dashscope",
            embedding_model="test-model",
            embedding_dimensions=1024,
            embedding_chunk_size=800,
            embedding_chunk_overlap=120,
            embedding_api_key="unused-test-key",
            rerank_provider="dashscope",
            rerank_model="test-rerank-model",
            rerank_api_key="unused-test-key",
        )
        self.source = self.root / "note.txt"
        self.source.write_bytes(b"original bytes\r\n")
        self.user = uuid4()
        self.store = Store([self.user])
        patched = patch.object(documents, "user_transaction", self.store.transaction)
        patched.start()
        self.addCleanup(patched.stop)

    def file_for(self, version):
        return self.settings.raw_storage_dir / version["storage_key"]

    def upload(self, document_id=None):
        return documents.upload_file(self.settings, self.user, self.source, document_id)

    def test_new_upload_persists_bytes_and_sets_latest(self):
        result = self.upload()
        version = next(iter(self.store.versions.values()))
        self.assertTrue(self.file_for(version).is_file(), "new upload must save the original")
        self.assertEqual(self.file_for(version).read_bytes(), self.source.read_bytes())
        document = self.store.documents[version["document_id"]]
        self.assertEqual(document["latest_version_id"], version["id"])
        self.assertEqual(document["title"], "note.txt")
        self.assertEqual(version["media_type"], "text/plain")
        self.assertEqual(result.document_id, document["id"])
        self.assertEqual(result.version_id, version["id"])
        self.assertTrue(result.created_document and result.created_version)

    def test_identical_latest_reuses_version_and_file(self):
        first = self.upload()
        second = self.upload(first.document_id)
        self.assertEqual(second.version_id, first.version_id)
        self.assertFalse(second.created_document or second.created_version)
        self.assertEqual(len(self.store.versions), 1)
        self.assertEqual(len(list(self.settings.raw_storage_dir.rglob("*.txt"))), 1)

    def test_update_keeps_original_and_returns_version(self):
        first = self.upload()
        old = self.store.versions[first.version_id]
        original = self.file_for(old).read_bytes()
        self.source.write_bytes(b"new content")
        second = self.upload(first.document_id)
        self.assertEqual(self.file_for(old).read_bytes(), original)
        self.assertNotEqual(first.storage_key, second.storage_key)
        self.assertEqual(second.version_no, 2)
        self.assertEqual(self.file_for(self.store.versions[second.version_id]).read_bytes(), b"new content")
        self.assertTrue(second.created_version)
        self.assertFalse(second.created_document)

    def test_a_b_a_produces_three_immutable_versions(self):
        first = self.upload()
        self.source.write_bytes(b"B")
        self.upload(first.document_id)
        self.source.write_bytes(b"original bytes\r\n")
        last = self.upload(first.document_id)
        self.assertEqual(last.version_no, 3)
        self.assertEqual(len(self.store.versions), 3)
        for version in self.store.versions.values():
            self.assertEqual(sha256(self.file_for(version).read_bytes()).hexdigest(), version["raw_sha256"])

    def test_same_name_in_different_documents_does_not_collide(self):
        first = self.upload()
        self.source.write_bytes(b"another document")
        second = self.upload()
        self.assertNotEqual(first.document_id, second.document_id)
        self.assertNotEqual(first.storage_key, second.storage_key)
        self.assertEqual(self.file_for(self.store.versions[first.version_id]).read_bytes(), b"original bytes\r\n")

    def test_unknown_or_other_user_document_does_not_write_file(self):
        with self.assertRaises(ValueError):
            self.upload(uuid4())
        self.assertFalse(self.settings.raw_storage_dir.exists())
        first = self.upload()
        other = uuid4()
        with self.assertRaises(ValueError):
            documents.upload_file(self.settings, other, self.source, first.document_id)
        self.assertFalse((self.settings.raw_storage_dir / str(other)).exists())

    def test_empty_existing_document_can_receive_first_version(self):
        document_id = uuid4()
        self.store.documents[document_id] = {"id": document_id, "user_id": self.user, "latest_version_id": None}
        result = self.upload(document_id)
        self.assertEqual(result.version_no, 1)

    def test_database_statement_failure_rolls_back_and_cleans_new_file(self):
        self.store.fail_version_insert = True
        with self.assertRaises(CheckViolation):
            self.upload()
        self.assertEqual(self.store.documents, {})
        self.assertEqual(self.store.versions, {})
        self.assertEqual([p for p in self.settings.raw_storage_dir.rglob("*") if p.is_file()], [])

    def test_uncertain_commit_retains_file_instead_of_risking_dangling_reference(self):
        self.store.fail_commit = True
        with self.assertRaises(OperationalError):
            self.upload()
        self.assertEqual(self.store.versions, {})
        files = [p for p in self.settings.raw_storage_dir.rglob("*") if p.is_file()]
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].read_bytes(), b"original bytes\r\n")

    def test_missing_historical_file_is_not_reported_as_duplicate_success(self):
        first = self.upload()
        self.file_for(self.store.versions[first.version_id]).unlink()
        with self.assertRaises(FileNotFoundError):
            self.upload(first.document_id)

    def test_source_change_after_read_cannot_change_saved_snapshot(self):
        original = self.source.read_bytes()
        self.store.before_version_insert = lambda: self.source.write_bytes(b"source changed")
        result = self.upload()
        saved = self.file_for(self.store.versions[result.version_id]).read_bytes()
        self.assertEqual(saved, original)
        self.assertEqual(sha256(saved).hexdigest(), self.store.versions[result.version_id]["raw_sha256"])

    def test_file_publish_failure_leaves_no_database_rows_or_temporary_file(self):
        with patch("documents.os.replace", side_effect=OSError("simulated disk failure")):
            with self.assertRaises(OSError):
                self.upload()
        self.assertEqual(self.store.documents, {})
        self.assertEqual([p for p in self.settings.raw_storage_dir.rglob("*") if p.is_file()], [])


if __name__ == "__main__":
    unittest.main()
