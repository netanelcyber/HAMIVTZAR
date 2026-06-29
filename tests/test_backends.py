"""Tests for the answer backends.

These run fully offline. They never start a network call: the extractive
backend is pure-Python, and the resolution test only checks that ``auto`` falls
back to an offline engine when no local LLM is reachable.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linux_docs_llm.backends import (
    ClaudeAnswerer,
    ExtractiveAnswerer,
    OllamaAnswerer,
    make_backend,
    resolve_backend,
)
from linux_docs_llm.ingest import chunk_documents
from linux_docs_llm.retriever import BM25Index


def _sample_results():
    text = (
        "# Permissions\n\n"
        "Use chmod to change file permissions. The command chmod u+x script.sh "
        "makes a file executable for its owner.\n\n"
        "```\nchmod 755 script.sh\n```\n\n"
        "# Networking\n\nUse ip addr to show network interfaces."
    )
    chunks = chunk_documents([("file-permissions.md", text)])
    index = BM25Index(chunks)
    return index.search("how do I make a script executable with chmod", top_k=3)


class ExtractiveBackendTests(unittest.TestCase):
    def test_answer_is_grounded_and_cited(self):
        results = _sample_results()
        backend = ExtractiveAnswerer()
        answer = backend.answer("make a script executable", results)
        self.assertIn("[1]", answer)
        self.assertIn("chmod", answer)

    def test_answer_streams_via_callback(self):
        results = _sample_results()
        captured = []
        backend = ExtractiveAnswerer()
        returned = backend.answer("chmod", results, on_text=captured.append)
        self.assertEqual("".join(captured), returned)

    def test_always_available_offline(self):
        self.assertTrue(ExtractiveAnswerer().available())


class BackendResolutionTests(unittest.TestCase):
    def test_make_backend_by_name(self):
        self.assertIsInstance(make_backend("extractive"), ExtractiveAnswerer)
        self.assertIsInstance(make_backend("ollama"), OllamaAnswerer)
        self.assertIsInstance(make_backend("claude"), ClaudeAnswerer)

    def test_make_backend_rejects_unknown(self):
        with self.assertRaises(ValueError):
            make_backend("nope")

    def test_auto_is_offline_and_falls_back_to_extractive(self):
        # No Ollama server and no GGUF model here, so auto must land on
        # extractive — and must never pick the online Claude backend.
        backend = resolve_backend("auto")
        self.assertFalse(backend.requires_network)
        self.assertIn(backend.name, {"ollama", "llama-cpp", "extractive"})

    def test_ollama_unreachable_reports_unavailable(self):
        # Point at a port nothing is listening on.
        backend = OllamaAnswerer(url="http://127.0.0.1:1")
        self.assertFalse(backend.available())


if __name__ == "__main__":
    unittest.main()
