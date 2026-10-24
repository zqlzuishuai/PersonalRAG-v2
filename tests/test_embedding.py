import asyncio
import json
import unittest
from unittest.mock import Mock, patch

import embedding


class EmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.config = {"provider": "aliyun", "model": "qwen3.7-text-embedding-flash", "dimensions": 1024}

    def call(self, vectors, texts=None):
        with patch.object(embedding, "required_env", side_effect=lambda name: "test-key" if name.endswith("KEY") else "https://example.invalid/v1"):
            with patch.object(embedding, "OpenAIEmbeddings") as factory:
                factory.return_value.embed_documents.return_value = vectors
                result = embedding.embed_texts(["正文"] if texts is None else texts, self.config)
                if result:
                    self.assertFalse(factory.call_args.kwargs["check_embedding_ctx_length"])
                    self.assertEqual(factory.call_args.kwargs["dimensions"], 1024)
                return result

    def test_returns_vectors_in_input_order(self):
        vectors = [[1.0] * 1024, [2.0] * 1024]
        self.assertEqual(self.call(vectors, ["第一段", "第二段"]), vectors)

    def test_rejects_wrong_vector_count(self):
        with self.assertRaises(ValueError):
            self.call([])

    def test_rejects_wrong_dimensions_zero_and_nonfinite_vectors(self):
        for vector in ([1.0] * 768, [0.0] * 1024, [float("nan")] * 1024, [float("inf")] * 1024):
            with self.subTest(first=vector[0]):
                with self.assertRaises(ValueError):
                    self.call([vector])

    def test_empty_input_does_not_construct_api_client(self):
        with patch.object(embedding, "OpenAIEmbeddings") as factory:
            self.assertEqual(embedding.embed_texts([], self.config), [])
            factory.assert_not_called()

    def test_real_langchain_client_sends_raw_strings_in_batches_of_ten(self):
        import httpx
        from langchain_openai import OpenAIEmbeddings

        batches = []

        def respond(request):
            self.assertEqual(request.url.host, "example.invalid")
            self.assertEqual(request.url.path, "/v1/embeddings")
            body = json.loads(request.content)
            self.assertEqual(body["dimensions"], 1024)
            self.assertEqual(body["encoding_format"], "float")
            self.assertTrue(all(isinstance(t, str) for t in body["input"]))
            batches.append(len(body["input"]))
            return httpx.Response(200, json={
                "object": "list", "model": self.config["model"],
                "data": [{"object": "embedding", "index": i, "embedding": [1.0] * 1024} for i in range(len(body["input"]))],
                "usage": {"prompt_tokens": 1, "total_tokens": 1},
            })

        transport = httpx.MockTransport(respond)
        async_client = httpx.AsyncClient(transport=transport)
        try:
            with httpx.Client(transport=transport) as http_client:
                def factory(**kwargs):
                    return OpenAIEmbeddings(**kwargs, http_client=http_client, http_async_client=async_client)
                with patch.object(embedding, "required_env", side_effect=lambda n: "test-key" if n.endswith("KEY") else "https://example.invalid/v1"):
                    with patch.object(embedding, "OpenAIEmbeddings", side_effect=factory):
                        result = embedding.embed_texts(["中文原文"] * 11, self.config)
            self.assertEqual(batches, [10, 1])
            self.assertEqual(len(result), 11)
        finally:
            asyncio.run(async_client.aclose())


if __name__ == "__main__":
    unittest.main()
