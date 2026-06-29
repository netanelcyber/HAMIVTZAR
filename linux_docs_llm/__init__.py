"""A retrieval-augmented LLM system grounded in Linux documentation.

The package wires three pieces together:

* ``ingest``    – load a directory of docs and split them into chunks.
* ``retriever`` – a dependency-free BM25 index over those chunks.
* ``llm``       – ask Claude a question using the retrieved chunks as context.

See ``cli`` for the command-line entry point.
"""

from .ingest import Chunk, iter_documents, chunk_documents
from .retriever import BM25Index
from .llm import LinuxDocsLLM, DEFAULT_MODEL

__all__ = [
    "Chunk",
    "iter_documents",
    "chunk_documents",
    "BM25Index",
    "LinuxDocsLLM",
    "DEFAULT_MODEL",
]

__version__ = "0.1.0"
