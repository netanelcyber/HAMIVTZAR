"""Load documentation files and split them into retrievable chunks.

The chunker is intentionally simple and format-agnostic: it groups
blank-line-separated paragraphs into ~``target_words`` chunks and remembers the
nearest preceding Markdown heading so each chunk carries a little context.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Iterable, Iterator, List

# Text extensions we treat as documentation.
DOC_EXTENSIONS = (".md", ".markdown", ".rst", ".txt")


@dataclass
class Chunk:
    """A single retrievable passage extracted from a document."""

    id: int
    source: str          # path relative to the docs root
    heading: str         # nearest preceding heading, "" if none
    text: str            # the chunk body

    def as_context(self) -> str:
        """Render the chunk the way it is shown to the model."""
        title = f"{self.source}" + (f" — {self.heading}" if self.heading else "")
        return f"{title}\n{self.text}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Chunk":
        return cls(
            id=data["id"],
            source=data["source"],
            heading=data.get("heading", ""),
            text=data["text"],
        )


def iter_documents(root: str) -> Iterator[tuple[str, str]]:
    """Yield ``(relative_path, text)`` for every doc file under ``root``.

    ``root`` may be a single file or a directory (walked recursively).
    """
    if os.path.isfile(root):
        with open(root, "r", encoding="utf-8", errors="replace") as fh:
            yield os.path.basename(root), fh.read()
        return

    for dirpath, _dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            if not name.lower().endswith(DOC_EXTENSIONS):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                yield rel, fh.read()


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and stripped.startswith("#")


def _clean_heading(line: str) -> str:
    return line.strip().lstrip("#").strip()


def _split_paragraphs(text: str) -> Iterator[tuple[str, str]]:
    """Yield ``(heading, paragraph)`` pairs, tracking the current heading."""
    heading = ""
    buffer: List[str] = []

    def flush() -> Iterator[tuple[str, str]]:
        if buffer:
            para = "\n".join(buffer).strip()
            if para:
                yield heading, para
        buffer.clear()

    for line in text.splitlines():
        if _is_heading(line):
            yield from flush()
            heading = _clean_heading(line)
        elif line.strip() == "":
            yield from flush()
        else:
            buffer.append(line)
    yield from flush()


def chunk_documents(
    documents: Iterable[tuple[str, str]],
    target_words: int = 180,
) -> List[Chunk]:
    """Turn ``(source, text)`` documents into a flat list of :class:`Chunk`.

    Paragraphs sharing a heading are packed together until ``target_words`` is
    reached, so chunks stay topically coherent without being too large.
    """
    chunks: List[Chunk] = []
    next_id = 0

    for source, text in documents:
        current_heading = ""
        pending: List[str] = []
        pending_words = 0

        def emit() -> None:
            nonlocal next_id, pending, pending_words
            if pending:
                chunks.append(
                    Chunk(
                        id=next_id,
                        source=source,
                        heading=current_heading,
                        text="\n\n".join(pending).strip(),
                    )
                )
                next_id += 1
                pending = []
                pending_words = 0

        for heading, paragraph in _split_paragraphs(text):
            if heading != current_heading:
                emit()
                current_heading = heading
            words = len(paragraph.split())
            if pending and pending_words + words > target_words:
                emit()
            pending.append(paragraph)
            pending_words += words
        emit()

    return chunks
