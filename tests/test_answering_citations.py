"""Citation validation tests; no database or model API calls."""
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from langchain_core.messages import AIMessage

import answering
from rerank import RerankChunk
from retrieval import RecallChunk


class AnswerCitationTests(unittest.TestCase):
    def setUp(self):
        self.settings = object()
        self.user = uuid4()
        self.sources = [
            RerankChunk(
                RecallChunk(uuid4(), uuid4(), uuid4(), uuid4(),
                            "参考正文", {"ordinal": i}),
                rerank_score=0.9,
            )
            for i in range(2)
        ]
        self.chat = Mock()

    def generate(self, content, sources=None):
        sources = self.sources if sources is None else sources
        self.chat.invoke.return_value = AIMessage(content=content)
        with patch.object(answering, "hybrid_recall", return_value=[s.chunk for s in sources]):
            with patch.object(answering, "rerank_chunks", return_value=sources):
                return answering.generate_system_message(
                    self.settings, self.user, self.chat, "测试问题"
                )

    def test_valid_repeated_citations_preserve_answer_and_sources(self):
        result = self.generate("结论。[1][2] 补充。[1]")
        self.assertEqual(result.ai_message.content, "结论。[1][2] 补充。[1]")
        self.assertIs(result.sources, self.sources)

    def test_out_of_range_citations_raise(self):
        for number in (0, 3, 999):
            with self.subTest(number=number):
                with self.assertRaisesRegex(ValueError, str(number)):
                    self.generate(f"结论。[{number}]")

    def test_mixed_valid_and_invalid_citations_raise(self):
        with self.assertRaisesRegex(ValueError, "999"):
            self.generate("结论。[1][999]")

    def test_no_citation_text_is_allowed(self):
        result = self.generate("当前检索到的资料不足以回答这个问题。")
        self.assertEqual(result.sources, self.sources)

    def test_citation_with_zero_sources_raises(self):
        with self.assertRaises(ValueError):
            self.generate("结论。[1]", sources=[])

    def test_non_text_model_content_is_rejected(self):
        with self.assertRaises(TypeError):
            self.generate([{"type": "text", "text": "结论。[1]"}])


if __name__ == "__main__":
    unittest.main()
