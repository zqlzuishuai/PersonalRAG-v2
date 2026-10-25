import unittest
from unittest.mock import patch
from uuid import uuid4

import main
from config import Settings
from pathlib import Path
from tests.fakes import Store


class IsolationCheckTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b = uuid4(), uuid4()
        self.store = Store([self.a, self.b])
        self.settings = Settings(
            app_database_url="unused",
            auth_database_url="unused",
            raw_storage_dir=Path("unused"),
            chat_model_api_key="unused-test-key",
            chat_model_base_url="https://example.invalid/v1",
            chat_model_provider="openai",
            chat_model_name="test-chat-model",
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
        patched = patch.object(main, "user_transaction", self.store.transaction)
        patched.start()
        self.addCleanup(patched.stop)

    def test_expected_foreign_key_refusal_passes_and_cleans_fixtures(self):
        main.check_user_isolation(self.settings, self.a, self.b)
        self.assertEqual(self.store.documents, {})
        self.assertEqual(self.store.folders, {})

    def test_unexpected_success_raises_instead_of_printing_success(self):
        self.store.allow_cross_user_folder = True
        with self.assertRaises(AssertionError):
            main.check_user_isolation(self.settings, self.a, self.b)
        self.assertEqual(self.store.documents, {})
        self.assertEqual(self.store.folders, {})

    def test_missing_test_user_is_not_mistaken_for_isolation_success(self):
        self.store.users.remove(self.b)
        with self.assertRaises(ValueError):
            main.check_user_isolation(self.settings, self.a, self.b)
        self.assertEqual(self.store.folders, {})


if __name__ == "__main__":
    unittest.main()
