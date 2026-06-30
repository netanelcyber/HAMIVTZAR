"""
Text pre-processing pipeline using NLTK.

Used before BPE tokeniser training to clean and normalise the corpus.
Steps:
  1. Sentence tokenisation (punkt)
  2. Word-level normalisation (lowercase optional, punctuation handling)
  3. Stopword statistics (for diagnostics, not filtering — we want the LM
     to learn function words too)
  4. Lemmatisation for vocabulary analysis / reporting

The cleaned text is returned as a single string ready for BPE training.
"""

import re
import unicodedata
from typing import Optional

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords as nltk_stopwords
    from nltk.stem import WordNetLemmatizer

    # Download required data silently
    for pkg in ("punkt_tab", "stopwords", "wordnet", "omw-1.4"):
        try:
            nltk.download(pkg, quiet=True)
        except Exception:
            pass

    _NLTK_AVAILABLE = True
except ImportError:
    _NLTK_AVAILABLE = False


# ---------------------------------------------------------------------------
# Cleaning helpers
# ---------------------------------------------------------------------------

# Characters to strip from the corpus (control chars, zero-width, etc.)
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
# Collapse runs of whitespace to single space (but keep newlines)
_SPACE_RE = re.compile(r"[^\S\n]+")
# Lines that are pure noise: page numbers, troff leftovers, single symbols
_NOISE_LINE_RE = re.compile(r"^\s*(\d+|[^a-zA-Z0-9]{1,3})\s*$")


def _normalize_unicode(text: str) -> str:
    """Replace typographic quotes, dashes, etc. with ASCII equivalents."""
    replacements = {
        "‘": "'", "’": "'", "“": '"', "”": '"',
        "–": "-", "—": "--", "…": "...",
        " ": " ",   # non-breaking space
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    # Decompose and strip combining marks (accents on ASCII letters)
    text = unicodedata.normalize("NFC", text)
    return text


def _remove_noise_lines(text: str) -> str:
    lines = text.splitlines()
    cleaned = [l for l in lines if not _NOISE_LINE_RE.match(l)]
    return "\n".join(cleaned)


def clean_text(text: str) -> str:
    """
    Basic cleaning: control chars, unicode normalisation, noise lines,
    whitespace normalisation.  Does NOT lowercase — we want the LM to
    learn casing.
    """
    text = _CTRL_RE.sub(" ", text)
    text = _normalize_unicode(text)
    text = _remove_noise_lines(text)
    text = _SPACE_RE.sub(" ", text)
    # Collapse 3+ blank lines → 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# NLTK-based sentence splitting and word normalisation
# ---------------------------------------------------------------------------

def sentence_split(text: str) -> list[str]:
    """Split text into sentences using NLTK punkt."""
    if not _NLTK_AVAILABLE:
        # Naive fallback
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    try:
        return sent_tokenize(text)
    except Exception:
        return [text]


def word_tokenize_nltk(sentence: str) -> list[str]:
    """Tokenise a sentence into words using NLTK."""
    if not _NLTK_AVAILABLE:
        return sentence.split()
    try:
        return word_tokenize(sentence)
    except Exception:
        return sentence.split()


# ---------------------------------------------------------------------------
# Vocabulary analysis (diagnostic — not used in training loop)
# ---------------------------------------------------------------------------

def analyze_corpus(text: str, top_n: int = 20) -> dict:
    """
    Return basic corpus statistics using NLTK.
    Useful for understanding the training data.
    """
    if not _NLTK_AVAILABLE:
        words = text.lower().split()
        from collections import Counter
        return {"words": len(words), "unique": len(set(words)),
                "top": Counter(words).most_common(top_n)}

    from collections import Counter

    try:
        words = word_tokenize(text.lower())
    except Exception:
        words = text.lower().split()

    total = len(words)
    unique = len(set(words))

    try:
        sw = set(nltk_stopwords.words("english"))
        content_words = [w for w in words if w.isalpha() and w not in sw]
    except Exception:
        content_words = [w for w in words if w.isalpha()]

    freq = Counter(content_words)

    lemmatizer = WordNetLemmatizer() if _NLTK_AVAILABLE else None
    top_lemmatised = []
    for word, count in freq.most_common(top_n):
        lemma = lemmatizer.lemmatize(word) if lemmatizer else word
        top_lemmatised.append((lemma, count))

    return {
        "total_words": total,
        "unique_words": unique,
        "type_token_ratio": round(unique / max(total, 1), 4),
        "content_word_count": len(content_words),
        "top_content_words": top_lemmatised,
        "nltk_available": _NLTK_AVAILABLE,
    }


# ---------------------------------------------------------------------------
# Main pre-processing entry point
# ---------------------------------------------------------------------------

def preprocess_corpus(text: str, analyze: bool = True) -> tuple[str, Optional[dict]]:
    """
    Clean and normalise the corpus text.
    Returns (cleaned_text, stats_dict_or_None).
    """
    cleaned = clean_text(text)

    stats = None
    if analyze and _NLTK_AVAILABLE:
        # Analyse a 100KB sample for speed
        sample = cleaned[:100_000]
        stats = analyze_corpus(sample)

    return cleaned, stats
