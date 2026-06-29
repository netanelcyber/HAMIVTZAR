"""Prompt assembly shared by every answer backend.

Keeping the system prompt and context formatting here lets the Claude, Ollama,
and llama.cpp backends all speak to their model with identical instructions.
"""

from __future__ import annotations

from typing import List, Tuple

from .ingest import Chunk

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

# Shown when retrieval finds nothing relevant — no backend is called.
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
    return f"Documentation excerpts:\n\n{context}\n\n---\n\nQuestion: {question}"
