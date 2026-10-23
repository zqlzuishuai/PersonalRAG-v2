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
        self.settings = Settings("unused", "unused", Path("unused"))
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
