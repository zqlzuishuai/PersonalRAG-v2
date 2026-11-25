import tempfile
import unittest
from contextlib import ExitStack
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import UUID

from starlette.testclient import TestClient

from web_app import create_app


class DocumentContentTests(unittest.TestCase):
    def setUp(self):
        stack = self.enterContext(ExitStack())
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        self.user, self.other, self.document, self.version = map(lambda n: UUID(int=n), range(1, 5))
        self.path = f"/api/documents/{self.document}/versions/{self.version}/content"
        self.origin = "https://rag.example.test"
        self.content = "# 原文\n<script>仅作文本</script>\n"
        original = self.content.encode()
        (self.root / "source.md").write_bytes(original)
        self.row = dict(storage_key="source.md", raw_sha256=sha256(original).hexdigest(),
                        byte_size=len(original), version_no=2, media_type="text/markdown")
        cursor = Mock()
        cursor.execute.side_effect = self.lookup
        transaction = stack.enter_context(patch("documents.user_transaction"))
        transaction.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = cursor
        env = {"PERSONALRAG_WEB_SESSION_SECRET": "test-session-key", "PERSONALRAG_WEB_ORIGIN": self.origin}
        stack.enter_context(patch("web_app.required_env", side_effect=env.__getitem__))
        stack.enter_context(patch("web_app.env_bool", side_effect=lambda key, default: default))
        stack.enter_context(patch("web_app.load_settings", return_value=SimpleNamespace(raw_storage_dir=self.root)))
        stack.enter_context(patch("web_app.authenticate_password", side_effect=lambda _, name, password:
                                  self.user if name == "alice" else self.other))
        self.client = stack.enter_context(TestClient(create_app(), base_url=self.origin))

    def lookup(self, query, params):
        self.assertIn("d.deleted_at IS NULL", query)
        self.assertIn("v.document_id = d.id", query)
        self.assertIn("v.user_id = d.user_id", query)
        return Mock(fetchone=Mock(return_value=self.row if params == (self.user, self.document, self.version) else None))

    def login(self, name="alice"):
        response = self.client.post("/api/auth/login", headers={"Origin": self.origin},
                                    json={"login_name": name, "password": "test-password"})
        self.assertEqual(response.status_code, 200, response.text)

    def test_owner_reads_literal_original_and_response_is_not_cached(self):
        self.login()
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"content": self.content, "version_no": 2, "media_type": "text/markdown"})
        self.assertIn("no-store", response.headers["cache-control"])

    def test_anonymous_wrong_document_version_and_other_account(self):
        self.assertEqual(self.client.get(self.path).status_code, 401)
        self.login()
        self.assertEqual(self.client.get(self.path.replace(str(self.document), str(UUID(int=8)))).status_code, 404)
        self.assertEqual(self.client.get(self.path.replace(str(self.version), "invalid")).status_code, 400)
        self.assertEqual(self.client.get(self.path.replace(str(self.version), str(UUID(int=9)))).status_code, 404)
        self.login("bob")
        self.assertEqual(self.client.get(self.path).status_code, 404)

    def test_missing_damaged_and_invalid_storage_do_not_return_content(self):
        self.login()
        source = self.root / "source.md"
        source.write_bytes(b"x" * self.row["byte_size"])
        self.assertEqual(self.client.get(self.path).status_code, 503)
        source.unlink()
        self.assertEqual(self.client.get(self.path).status_code, 503)
        self.row["storage_key"] = "../outside.md"
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("outside.md", response.text)
