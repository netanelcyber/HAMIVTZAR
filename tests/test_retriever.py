"""Tests for the ingestion and BM25 retrieval pipeline.

These run fully offline — no API key or network required.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linux_docs_llm.ingest import chunk_documents, iter_documents
from linux_docs_llm.retriever import BM25Index, tokenize

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "docs")


class TokenizeTests(unittest.TestCase):
    def test_lowercases_and_splits(self):
        self.assertEqual(tokenize("Chmod 755 FILE.txt"), ["chmod", "755", "file", "txt"])

    def test_keeps_underscores(self):
        self.assertEqual(tokenize("multi_user.target"), ["multi_user", "target"])


class ChunkingTests(unittest.TestCase):
    def test_chunks_track_headings(self):
        text = "# Title\n\nFirst paragraph here.\n\n## Section\n\nSecond paragraph."
        chunks = chunk_documents([("doc.md", text)], target_words=50)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].heading, "Title")
        self.assertEqual(chunks[1].heading, "Section")
        self.assertIn("First paragraph", chunks[0].text)

    def test_target_words_splits_long_sections(self):
        body = "\n\n".join("word " * 60 for _ in range(4))
        text = f"# Big\n\n{body}"
        chunks = chunk_documents([("doc.md", text)], target_words=100)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(c.heading == "Big" for c in chunks))

    def test_ids_are_unique_and_sequential(self):
        text = "# A\n\np1\n\n# B\n\np2\n\n# C\n\np3"
        chunks = chunk_documents([("doc.md", text)])
        self.assertEqual([c.id for c in chunks], [0, 1, 2])


class BM25Tests(unittest.TestCase):
    def setUp(self):
        text = (
            "# Permissions\n\nUse chmod to change file permissions.\n\n"
            "# Processes\n\nUse kill to send a signal to a process.\n\n"
            "# Networking\n\nUse ip addr to show network interfaces."
        )
        self.chunks = chunk_documents([("doc.md", text)])
        self.index = BM25Index(self.chunks)

    def test_search_ranks_relevant_chunk_first(self):
        results = self.index.search("how do I change permissions with chmod", top_k=3)
        self.assertTrue(results)
        top_chunk, top_score = results[0]
        self.assertIn("chmod", top_chunk.text)
        self.assertGreater(top_score, 0)

    def test_search_filters_zero_scores(self):
        results = self.index.search("kill signal process", top_k=5)
        self.assertTrue(all(score > 0 for _chunk, score in results))
        self.assertIn("kill", results[0][0].text)

    def test_no_match_returns_empty(self):
        results = self.index.search("zzzznotarealword", top_k=5)
        self.assertEqual(results, [])

    def test_roundtrip_save_load(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            path = fh.name
        try:
            self.index.save(path)
            loaded = BM25Index.load(path)
            self.assertEqual(len(loaded), len(self.index))
            r1 = self.index.search("chmod permissions")
            r2 = loaded.search("chmod permissions")
            self.assertEqual([c.id for c, _ in r1], [c.id for c, _ in r2])
        finally:
            os.unlink(path)


class SampleCorpusTests(unittest.TestCase):
    """Smoke test against the shipped Linux docs."""

    def test_index_sample_docs_and_query(self):
        documents = list(iter_documents(DOCS_DIR))
        self.assertGreaterEqual(len(documents), 5)
        index = BM25Index(chunk_documents(documents))
        self.assertGreater(len(index), len(documents))

        results = index.search("how to make a file executable", top_k=3)
        self.assertTrue(results)
        self.assertEqual(results[0][0].source, "file-permissions.md")


if __name__ == "__main__":
    unittest.main()
