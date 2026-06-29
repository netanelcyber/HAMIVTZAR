"""Tie retrieval and an answer backend together.

:class:`LinuxDocsLLM` retrieves documentation chunks for a question and hands
them to a pluggable :class:`~linux_docs_llm.backends.Answerer`. The default
backend is fully offline (see :mod:`linux_docs_llm.backends`).
"""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from .backends import Answerer, resolve_backend
from .ingest import Chunk
from .prompt import NO_CONTEXT_MESSAGE
from .retriever import BM25Index

# Kept for backwards compatibility / convenience imports.
from .backends import DEFAULT_CLAUDE_MODEL as DEFAULT_MODEL  # noqa: F401


class LinuxDocsLLM:
    """Retrieve relevant chunks and answer a question with the given backend."""

    def __init__(
        self,
        index: BM25Index,
        backend: Optional[Answerer] = None,
        top_k: int = 4,
    ):
        self.index = index
        self.backend = backend or resolve_backend("auto")
        self.top_k = top_k

    def retrieve(self, question: str) -> List[Tuple[Chunk, float]]:
        return self.index.search(question, top_k=self.top_k)

    def answer(
        self,
        question: str,
        on_text: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, List[Tuple[Chunk, float]]]:
        """Answer ``question`` and return ``(answer_text, retrieved_chunks)``.

        If ``on_text`` is given it receives streamed text deltas (used by the CLI
        to print the answer as it is produced). When retrieval finds nothing, the
        backend is not called and a fixed "no context" message is returned.
        """
        results = self.retrieve(question)
        if not results:
            if on_text:
                on_text(NO_CONTEXT_MESSAGE)
            return NO_CONTEXT_MESSAGE, results

        text = self.backend.answer(question, results, on_text=on_text)
        return text, results
