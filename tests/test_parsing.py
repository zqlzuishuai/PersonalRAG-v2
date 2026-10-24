import unittest
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import parsing


class SplitTextTests(unittest.TestCase):
    def test_empty_or_whitespace_returns_no_chunks(self):
        for text in ("", " \n\t "):
            with self.subTest(text=repr(text)):
                self.assertEqual(parsing.split_text(text), [])

    def test_short_text_remains_one_complete_chunk(self):
        text = "这是一段用于测试的短文本。"
        self.assertEqual(parsing.split_text(text), [text])

    def test_long_text_has_nonempty_bounded_chunks_without_gaps(self):
        # 每个字符不同，方便检查分块是否按原文顺序覆盖完整内容。
        text = "".join(chr(0x4E00 + index) for index in range(2400))
        chunks = parsing.split_text(text)
        self.assertGreater(len(chunks), 1)
        covered_until = 0
        previous_start = -1
        for chunk in chunks:
            self.assertTrue(chunk.strip())
            self.assertLessEqual(len(chunk), 800)
            start = text.find(chunk)
            self.assertGreaterEqual(start, 0)
            self.assertGreater(start, previous_start)
            self.assertLessEqual(start, covered_until, "分块之间不能遗漏原文")
            covered_until = max(covered_until, start + len(chunk))
            previous_start = start
        self.assertEqual(covered_until, len(text))


class SplitFileIntegrityTests(unittest.TestCase):
    def parse_snapshot(self, original, stored):
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            key = "snapshot.txt"
            (root / key).write_bytes(stored)
            metadata = {
                "storage_key": key,
                "media_type": "text/plain",
                "raw_sha256": sha256(original).hexdigest(),
                "byte_size": len(original),
            }

            class Connection:
                def execute(self, query, params):
                    # Return only the columns actually requested by production SQL.
                    columns = query.lower().split("select", 1)[1].split("from", 1)[0]
                    row = tuple(metadata[column.strip()] for column in columns.split(","))
                    return SimpleNamespace(fetchone=lambda: row)

            @contextmanager
            def transaction(settings, user_id):
                yield Connection()

            with patch.object(parsing, "user_transaction", transaction):
                return parsing.split_file(
                    SimpleNamespace(raw_storage_dir=root), uuid4(), uuid4()
                )

    def test_valid_snapshot_parses_multibyte_text(self):
        content = "原文完整性测试".encode("utf-8")
        self.assertEqual(self.parse_snapshot(content, content), [content.decode("utf-8")])

    def test_same_size_replacement_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.parse_snapshot(b"original", b"replaced")

    def test_truncated_snapshot_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "大小"):
            self.parse_snapshot(b"original", b"orig")

    def test_integrity_is_checked_before_utf8_decoding(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.parse_snapshot(b"original", b"\xff" * 8)


if __name__ == "__main__":
    unittest.main()
