"""Recall parameter tests: no database connections or external model calls."""
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

import retrieval


class RecallTopKTests(unittest.TestCase):
    def check_recall(self, name, top_k, error=None):
        connection = Mock()
        connection.execute.return_value.fetchall.return_value = []
        with patch.object(retrieval, "user_transaction") as transaction:
            transaction.return_value.__enter__.return_value = connection
            with patch.object(retrieval, "embed_texts", return_value=[[1.0] * 1024]) as embed:
                kwargs = {"top_k": top_k}
                if name != "keyword_recall":
                    kwargs["embedding_config"] = {
                        "provider": "aliyun", "model": "test-model", "dimensions": 1024,
                    }
                recall = getattr(retrieval, name)
                if error is not None:
                    with self.assertRaises(error):
                        recall(object(), uuid4(), "test question", **kwargs)
                    embed.assert_not_called()
                    transaction.assert_not_called()
                else:
                    self.assertEqual(recall(object(), uuid4(), "test question", **kwargs), [])
                    params = connection.execute.call_args.args[1]
                    actual_limit = params["top_k"] if isinstance(params, dict) else params[-1]
                    self.assertEqual(actual_limit, top_k)
                    self.assertIs(type(actual_limit), int)

    def test_boolean_top_k_is_rejected_before_external_calls(self):
        for name in ("semantic_recall", "keyword_recall", "hybrid_recall"):
            for top_k in (True, False):
                with self.subTest(function=name, top_k=top_k):
                    self.check_recall(name, top_k, TypeError)

    def test_out_of_range_top_k_is_rejected_before_external_calls(self):
        for name in ("semantic_recall", "keyword_recall", "hybrid_recall"):
            for top_k in (0, -1, 101):
                with self.subTest(function=name, top_k=top_k):
                    self.check_recall(name, top_k, ValueError)

    def test_non_integer_top_k_is_rejected_before_external_calls(self):
        for name in ("semantic_recall", "keyword_recall", "hybrid_recall"):
            for top_k in (1.5, "5", None):
                with self.subTest(function=name, top_k=top_k):
                    self.check_recall(name, top_k, TypeError)

    def test_integer_boundaries_reach_query_and_allow_empty_results(self):
        for name in ("semantic_recall", "keyword_recall", "hybrid_recall"):
            for top_k in (1, 100):
                with self.subTest(function=name, top_k=top_k):
                    self.check_recall(name, top_k)


if __name__ == "__main__":
    unittest.main()