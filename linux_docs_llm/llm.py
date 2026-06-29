"""Answer Linux questions with Claude, grounded in retrieved documentation.

The model is instructed to answer *only* from the provided context and to cite
the sources it used with ``[n]`` markers. Generation uses adaptive thinking and
streaming (per the Anthropic SDK guidance for anything non-trivial).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Optional, Tuple

from .ingest import Chunk
from .retriever import BM25Index

if TYPE_CHECKING:  # avoid importing the SDK unless it is actually used
    import anthropic

DEFAULT_MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """\
You are a Linux documentation assistant. Answer the user's question using ONLY \
the numbered documentation excerpts provided in the user message.

Rules:
- Ground every claim in the excerpts. Cite the excerpts you use with their \
number in square brackets, e.g. "Use chmod to change permissions [2]."
- If the excerpts do not contain the answer, say so plainly instead of guessing.
- Prefer concrete commands and short examples. Keep the answer focused; do not \
restate the whole excerpt.
- When you show a command, format it in a fenced code block.\
"""

# A message shown when retrieval finds nothing relevant — we skip the model call.
NO_CONTEXT_MESSAGE = (
    "I couldn't find anything relevant in the indexed Linux documentation. "
    "Try rephrasing, or add more docs and re-run `ingest`."
)


def format_context(results: List[Tuple[Chunk, float]]) -> str:
    """Render retrieved chunks as a numbered context block for the prompt."""
    blocks = []
    for n, (chunk, _score) in enumerate(results, start=1):
        blocks.append(f"[{n}] {chunk.as_context()}")
    return "\n\n".join(blocks)


def build_user_message(question: str, context: str) -> str:
    return (
        f"Documentation excerpts:\n\n{context}\n\n"
        f"---\n\nQuestion: {question}"
    )


class LinuxDocsLLM:
    """Couples a BM25 index with the Anthropic client to answer questions."""

    def __init__(
        self,
        index: BM25Index,
        client: Optional["anthropic.Anthropic"] = None,
        model: str = DEFAULT_MODEL,
        top_k: int = 4,
        max_tokens: int = 1500,
    ):
        self.index = index
        if client is None:
            import anthropic  # imported lazily so retrieval works without the SDK

            client = anthropic.Anthropic()
        self.client = client
        self.model = model
        self.top_k = top_k
        self.max_tokens = max_tokens

    def retrieve(self, question: str) -> List[Tuple[Chunk, float]]:
        return self.index.search(question, top_k=self.top_k)

    def answer(
        self,
        question: str,
        on_text: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, List[Tuple[Chunk, float]]]:
        """Answer ``question`` and return ``(answer_text, retrieved_chunks)``.

        If ``on_text`` is given it is called with each streamed text delta, which
        the CLI uses to print the answer as it is generated.
        """
        results = self.retrieve(question)
        if not results:
            if on_text:
                on_text(NO_CONTEXT_MESSAGE)
            return NO_CONTEXT_MESSAGE, results

        user_message = build_user_message(question, format_context(results))

        parts: List[str] = []
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                parts.append(text)
                if on_text:
                    on_text(text)

        return "".join(parts), results
