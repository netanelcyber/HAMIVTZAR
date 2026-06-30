"""
Byte Pair Encoding (BPE) tokenizer built from scratch.
Trained on Linux man-page text extracted at runtime.
"""

import re
import json
from collections import defaultdict
from pathlib import Path


def get_word_freqs(text: str) -> dict[str, int]:
    """Count whitespace-delimited token frequencies, splitting each word into chars."""
    freqs: dict[str, int] = defaultdict(int)
    for word in re.findall(r"\S+", text):
        # represent each word as space-separated characters with </w> end marker
        key = " ".join(list(word)) + " </w>"
        freqs[key] += 1
    return dict(freqs)


def get_pairs(vocab: dict[str, int]) -> dict[tuple[str, str], int]:
    """Count all adjacent symbol pairs across the vocab."""
    pairs: dict[tuple[str, str], int] = defaultdict(int)
    for word, freq in vocab.items():
        symbols = word.split()
        for i in range(len(symbols) - 1):
            pairs[(symbols[i], symbols[i + 1])] += freq
    return dict(pairs)


def merge_vocab(pair: tuple[str, str], vocab: dict[str, int]) -> dict[str, int]:
    """Merge the most frequent pair in every word in vocab."""
    merged = pair[0] + pair[1]
    escaped = re.escape(" ".join(pair))
    pattern = re.compile(r"(?<!\S)" + escaped + r"(?!\S)")
    return {pattern.sub(merged, word): freq for word, freq in vocab.items()}


class BPETokenizer:
    """Minimal BPE tokenizer."""

    PAD = "<PAD>"
    UNK = "<UNK>"
    BOS = "<BOS>"
    EOS = "<EOS>"
    SPECIAL = [PAD, UNK, BOS, EOS]

    def __init__(self) -> None:
        self.merges: list[tuple[str, str]] = []
        self.vocab: dict[str, int] = {}
        self.id2token: dict[int, str] = {}

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, text: str, vocab_size: int = 1000) -> None:
        """Learn BPE merges from *text* until *vocab_size* tokens."""
        word_freqs = get_word_freqs(text)

        # Base vocabulary: every unique character + special tokens
        chars: set[str] = set()
        for word in word_freqs:
            chars.update(word.split())

        all_tokens = self.SPECIAL + sorted(chars)
        self.vocab = {tok: i for i, tok in enumerate(all_tokens)}
        self.id2token = {i: tok for tok, i in self.vocab.items()}

        current_vocab = dict(word_freqs)
        num_merges = vocab_size - len(self.vocab)

        for _ in range(max(0, num_merges)):
            pairs = get_pairs(current_vocab)
            if not pairs:
                break
            best = max(pairs, key=pairs.get)  # type: ignore[arg-type]
            current_vocab = merge_vocab(best, current_vocab)
            self.merges.append(best)
            new_token = best[0] + best[1]
            if new_token not in self.vocab:
                idx = len(self.vocab)
                self.vocab[new_token] = idx
                self.id2token[idx] = new_token

    # ------------------------------------------------------------------
    # Encoding / Decoding
    # ------------------------------------------------------------------

    def _tokenize_word(self, word: str) -> list[str]:
        """Apply learned BPE merges to a single word."""
        symbols = list(word) + ["</w>"]
        merge_set = {pair: i for i, pair in enumerate(self.merges)}

        while len(symbols) > 1:
            pairs = [(symbols[i], symbols[i + 1]) for i in range(len(symbols) - 1)]
            # pick the pair with the lowest merge rank
            candidates = [(merge_set[p], i, p) for i, p in enumerate(pairs) if p in merge_set]
            if not candidates:
                break
            _, pos, best = min(candidates)
            merged = best[0] + best[1]
            symbols = symbols[:pos] + [merged] + symbols[pos + 2 :]

        return symbols

    def encode(self, text: str, add_special: bool = True) -> list[int]:
        tokens: list[str] = []
        if add_special:
            tokens.append(self.BOS)
        for word in re.findall(r"\S+", text):
            tokens.extend(self._tokenize_word(word))
        if add_special:
            tokens.append(self.EOS)
        unk_id = self.vocab[self.UNK]
        return [self.vocab.get(t, unk_id) for t in tokens]

    def decode(self, ids: list[int]) -> str:
        tokens = [self.id2token.get(i, self.UNK) for i in ids]
        # remove special tokens, join and strip BPE end-of-word marker
        text = " ".join(t for t in tokens if t not in self.SPECIAL)
        text = text.replace("</w> ", " ").replace(" </w>", "").replace("</w>", "")
        return text.strip()

    def __len__(self) -> int:
        return len(self.vocab)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        Path(path).write_text(
            json.dumps({"merges": self.merges, "vocab": self.vocab}, ensure_ascii=False, indent=2)
        )

    @classmethod
    def load(cls, path: str) -> "BPETokenizer":
        data = json.loads(Path(path).read_text())
        tok = cls()
        tok.merges = [tuple(m) for m in data["merges"]]  # type: ignore[misc]
        tok.vocab = data["vocab"]
        tok.id2token = {v: k for k, v in tok.vocab.items()}
        return tok
