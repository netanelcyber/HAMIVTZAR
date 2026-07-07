"""A dependency-free BM25 retriever over document chunks.

BM25 is a strong, well-understood ranking function for keyword-heavy technical
text (exactly what Linux docs are), and it needs no embeddings service, so the
whole pipeline runs offline. The index serializes to plain JSON.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from typing import Dict, List, Tuple

from .ingest import Chunk

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> List[str]:
    """Lowercase the text and split it into alphanumeric/underscore tokens."""
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    """An in-memory BM25 index over a list of :class:`Chunk`.

    Parameters ``k1`` and ``b`` are the standard BM25 knobs; the defaults are
    the usual general-purpose values.
    """

    def __init__(self, chunks: List[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self._doc_tokens: List[List[str]] = [tokenize(c.text + " " + c.heading) for c in chunks]
        self._doc_len: List[int] = [len(toks) for toks in self._doc_tokens]
        self._term_freqs: List[Counter] = [Counter(toks) for toks in self._doc_tokens]
        self._avgdl: float = (sum(self._doc_len) / len(self._doc_len)) if self._doc_len else 0.0
        self._idf: Dict[str, float] = self._compute_idf()

    def _compute_idf(self) -> Dict[str, float]:
        n = len(self.chunks)
        doc_freq: Counter = Counter()
        for tf in self._term_freqs:
            doc_freq.update(tf.keys())
        idf: Dict[str, float] = {}
        for term, df in doc_freq.items():
            # BM25 idf with +1 to keep scores non-negative.
            idf[term] = math.log(1 + (n - df + 0.5) / (df + 0.5))
        return idf

    def _score(self, query_tokens: List[str], doc_index: int) -> float:
        tf = self._term_freqs[doc_index]
        dl = self._doc_len[doc_index]
        score = 0.0
        for term in query_tokens:
            if term not in tf:
                continue
            idf = self._idf.get(term, 0.0)
            freq = tf[term]
            denom = freq + self.k1 * (1 - self.b + self.b * dl / (self._avgdl or 1))
            score += idf * (freq * (self.k1 + 1)) / (denom or 1)
        return score

    def search(self, query: str, top_k: int = 4) -> List[Tuple[Chunk, float]]:
        """Return the ``top_k`` highest-scoring chunks for ``query``.

        Chunks with a zero score (no query term matched) are omitted.
        """
        query_tokens = tokenize(query)
        scored = [
            (self.chunks[i], self._score(query_tokens, i))
            for i in range(len(self.chunks))
        ]
        scored = [pair for pair in scored if pair[1] > 0.0]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    # ------------------------------------------------------------------ I/O

    def save(self, path: str) -> None:
        payload = {
            "k1": self.k1,
            "b": self.b,
            "chunks": [c.to_dict() for c in self.chunks],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "BM25Index":
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        chunks = [Chunk.from_dict(d) for d in payload["chunks"]]
        return cls(chunks, k1=payload.get("k1", 1.5), b=payload.get("b", 0.75))

    def __len__(self) -> int:
        return len(self.chunks)
