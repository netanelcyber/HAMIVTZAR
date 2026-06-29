"""A retrieval-augmented LLM system grounded in Linux documentation.

Offline-first: the default answer backend runs disconnected (no network).

* ``ingest``    – load a directory of docs and split them into chunks.
* ``retriever`` – a dependency-free BM25 index over those chunks.
* ``backends``  – pluggable answer engines (extractive / Ollama / llama.cpp /
  Claude); ``auto`` selects an available offline engine.
* ``llm``       – retrieve chunks and answer with the chosen backend.

See ``cli`` for the command-line entry point.
"""

from .ingest import Chunk, iter_documents, chunk_documents
from .retriever import BM25Index
from .backends import (
    Answerer,
    ExtractiveAnswerer,
    OllamaAnswerer,
    LlamaCppAnswerer,
    ClaudeAnswerer,
    make_backend,
    resolve_backend,
    BACKEND_NAMES,
)
from .llm import LinuxDocsLLM, DEFAULT_MODEL

__all__ = [
    "Chunk",
    "iter_documents",
    "chunk_documents",
    "BM25Index",
    "Answerer",
    "ExtractiveAnswerer",
    "OllamaAnswerer",
    "LlamaCppAnswerer",
    "ClaudeAnswerer",
    "make_backend",
    "resolve_backend",
    "BACKEND_NAMES",
    "LinuxDocsLLM",
    "DEFAULT_MODEL",
]

__version__ = "0.2.0"
