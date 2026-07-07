"""Answer backends — pluggable engines that turn retrieved chunks into an answer.

The system is **offline-first**. The default ``auto`` backend selects, in order:

1. ``ollama``     – a local Ollama daemon (a real LLM, runs disconnected)
2. ``llama-cpp``  – a local GGUF model via ``llama-cpp-python`` (disconnected)
3. ``extractive`` – pure-Python, zero-dependency, always available offline

``claude`` (the Anthropic API) is online and is only used when requested
explicitly — ``auto`` never selects it, so the default configuration never
touches the network.

Every backend implements :meth:`Answerer.answer`, taking the question and the
retrieved ``(chunk, score)`` results and returning the answer text. An optional
``on_text`` callback receives streamed deltas for live terminal output.

The model-backed backends (Ollama, llama.cpp, Claude) also expose a lower-level
:meth:`ModelBackedAnswerer.generate` — "send this system + user message, stream
text back" — reused outside RAG question-answering too, e.g. by
``security_classifier.explain`` to turn classifier findings into a natural
language explanation with the same offline-first backend selection.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Callable, List, Optional, Tuple

from .ingest import Chunk
from .prompt import SYSTEM_PROMPT, build_user_message, format_context
from .retriever import tokenize

Results = List[Tuple[Chunk, float]]
OnText = Optional[Callable[[str], None]]


class Answerer:
    """Base class for answer backends."""

    name: str = "base"
    requires_network: bool = False

    def available(self) -> bool:  # pragma: no cover - overridden
        """Whether this backend can run right now (lib installed, server up…)."""
        return True

    def answer(self, question: str, results: Results, on_text: OnText = None) -> str:
        raise NotImplementedError

    @staticmethod
    def _emit(on_text: OnText, text: str) -> None:
        if on_text:
            on_text(text)


# --------------------------------------------------------------------------- #
# Offline: extractive (no model, no network, no dependencies)                  #
# --------------------------------------------------------------------------- #

_SENTENCE_RE = re.compile(r"(?<=[.!?:])\s+")
_FENCE_SPLIT_RE = re.compile(r"(```.*?```)", re.DOTALL)

# Low-value words ignored when scoring relevance, so a match on "a"/"to"/"how"
# never outranks a match on a real keyword like "chmod" or "executable".
_STOPWORDS = frozenset(
    """a an the and or but if then of to in on for with without my your his her its our
    do does did how what when where why which who whom is are was were be been being
    i you he she it we they me him them this that these those can could should would
    will shall may might must as at by from into out up down over under use using used
    get got make made want need please help thing things way ways""".split()
)


def _content_terms(text: str) -> set[str]:
    return {t for t in tokenize(text) if t not in _STOPWORDS and len(t) > 2}


class ExtractiveAnswerer(Answerer):
    """Build an answer directly from the retrieved text — no LLM involved.

    It returns the most query-relevant sentences from the top chunk (always
    keeping fenced command blocks intact) with a ``[1]`` citation, then points
    at the other matched sources. This guarantees a useful, fully offline answer
    even with no model installed.
    """

    name = "extractive"

    def available(self) -> bool:
        return True

    def _relevant_segments(self, text: str, query_terms: set[str], limit: int = 3) -> List[str]:
        # Split on fenced code blocks so prose and commands stay clean units.
        prose_units: List[str] = []
        code_units: List[str] = []
        for part in _FENCE_SPLIT_RE.split(text):
            part = part.strip()
            if not part:
                continue
            (code_units if part.startswith("```") else prose_units).append(part)

        scored = []  # (overlap, order, sentence)
        order = 0
        for unit in prose_units:
            for sentence in _SENTENCE_RE.split(unit):
                sentence = sentence.strip()
                if not sentence:
                    continue
                overlap = len(query_terms & _content_terms(sentence))
                if overlap:
                    scored.append((overlap, order, sentence))
                order += 1

        scored.sort(key=lambda t: (-t[0], t[1]))
        top = sorted(scored[:limit], key=lambda t: t[1])  # restore reading order
        chosen = [sentence for _ov, _idx, sentence in top]

        # Commands are usually the real answer in these docs — include the first
        # code block (it follows the matched prose, or stands alone if none matched).
        if code_units:
            chosen.append(code_units[0])
        if not chosen and prose_units:
            chosen.append(prose_units[0])
        return chosen

    def answer(self, question: str, results: Results, on_text: OnText = None) -> str:
        query_terms = _content_terms(question)
        top_chunk, _score = results[0]

        segments = self._relevant_segments(top_chunk.text, query_terms)
        body = "\n\n".join(segments) if segments else top_chunk.text

        lines = ["Based on the Linux documentation [1]:", "", body]
        if len(results) > 1:
            lines.append("")
            lines.append("Related sections:")
            for n, (chunk, _s) in enumerate(results[1:], start=2):
                label = chunk.source + (f" — {chunk.heading}" if chunk.heading else "")
                lines.append(f"  [{n}] {label}")

        text = "\n".join(lines)
        self._emit(on_text, text)
        return text


class ModelBackedAnswerer(Answerer):
    """Base for backends that call a real language model.

    Subclasses implement :meth:`generate` — the low-level "send a system +
    user message, stream text back" primitive. :meth:`answer` (the RAG
    question-answering entry point) is implemented once, here, in terms of it;
    other callers (e.g. ``security_classifier.explain``) can call
    :meth:`generate` directly for non-RAG natural-language tasks.
    """

    def generate(self, system: str, user_message: str, on_text: OnText = None) -> str:
        raise NotImplementedError

    def answer(self, question: str, results: Results, on_text: OnText = None) -> str:
        user_message = build_user_message(question, format_context(results))
        return self.generate(SYSTEM_PROMPT, user_message, on_text)


# --------------------------------------------------------------------------- #
# Offline: Ollama (local LLM daemon)                                           #
# --------------------------------------------------------------------------- #


def _no_proxy_opener() -> urllib.request.OpenerDirector:
    # localhost is in no_proxy, but build an explicitly proxy-free opener so a
    # local Ollama server is reached directly regardless of HTTP(S)_PROXY.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


class OllamaAnswerer(ModelBackedAnswerer):
    """Stream a response from a local `Ollama <https://ollama.com>`_ daemon.

    Fully offline once the model is pulled (``ollama pull llama3.2``). Talks to
    the daemon's HTTP API with the standard library only — no extra packages.
    """

    name = "ollama"

    def __init__(self, model: str = "llama3.2", url: Optional[str] = None):
        self.model = model
        self.url = (url or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        self._opener = _no_proxy_opener()

    def available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.url}/api/tags", method="GET")
            with self._opener.open(req, timeout=1.5):
                return True
        except Exception:
            return False

    def generate(self, system: str, user_message: str, on_text: OnText = None) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            "stream": True,
            "options": {"temperature": 0.2},
        }
        req = urllib.request.Request(
            f"{self.url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        parts: List[str] = []
        with self._opener.open(req, timeout=300) as resp:
            for raw in resp:  # Ollama streams newline-delimited JSON
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                event = json.loads(line)
                delta = event.get("message", {}).get("content", "")
                if delta:
                    parts.append(delta)
                    self._emit(on_text, delta)
                if event.get("done"):
                    break
        return "".join(parts)


# --------------------------------------------------------------------------- #
# Offline: llama.cpp (local GGUF model)                                        #
# --------------------------------------------------------------------------- #


class LlamaCppAnswerer(ModelBackedAnswerer):
    """Run a local GGUF model via ``llama-cpp-python`` — fully offline.

    Requires ``pip install llama-cpp-python`` and a model file, e.g.::

        --backend llama-cpp --model-path ./models/qwen2.5-1.5b-instruct-q4_k_m.gguf
    """

    name = "llama-cpp"

    def __init__(self, model_path: Optional[str] = None, n_ctx: int = 4096):
        self.model_path = model_path or os.environ.get("LLAMA_MODEL_PATH", "")
        self.n_ctx = n_ctx
        self._llm = None

    def available(self) -> bool:
        if not self.model_path or not os.path.exists(self.model_path):
            return False
        try:
            import llama_cpp  # noqa: F401
        except ImportError:
            return False
        return True

    def _load(self):
        if self._llm is None:
            from llama_cpp import Llama

            self._llm = Llama(model_path=self.model_path, n_ctx=self.n_ctx, verbose=False)
        return self._llm

    def generate(self, system: str, user_message: str, on_text: OnText = None) -> str:
        llm = self._load()
        stream = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=1024,
            stream=True,
        )
        parts: List[str] = []
        for chunk in stream:
            delta = chunk["choices"][0].get("delta", {}).get("content")
            if delta:
                parts.append(delta)
                self._emit(on_text, delta)
        return "".join(parts)


# --------------------------------------------------------------------------- #
# Online: Claude (Anthropic API) — opt-in only                                 #
# --------------------------------------------------------------------------- #

DEFAULT_CLAUDE_MODEL = "claude-opus-4-8"


class ClaudeAnswerer(ModelBackedAnswerer):
    """Answer with Claude via the Anthropic API. Requires network + an API key.

    This is the only online backend and is never chosen by ``auto``.
    """

    name = "claude"
    requires_network = True

    def __init__(self, model: str = DEFAULT_CLAUDE_MODEL, client=None, max_tokens: int = 1500):
        self.model = model
        self.max_tokens = max_tokens
        self._client = client

    def available(self) -> bool:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return bool(
            self._client
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        )

    def _client_or_create(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def generate(self, system: str, user_message: str, on_text: OnText = None) -> str:
        client = self._client_or_create()
        parts: List[str] = []
        with client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                parts.append(text)
                self._emit(on_text, text)
        return "".join(parts)


# --------------------------------------------------------------------------- #
# Backend selection                                                            #
# --------------------------------------------------------------------------- #

BACKEND_NAMES = ["auto", "extractive", "ollama", "llama-cpp", "claude"]

# Order tried by `auto` — every entry is offline; Claude is excluded on purpose.
_AUTO_ORDER = ["ollama", "llama-cpp", "extractive"]


def make_backend(name: str, **opts) -> Answerer:
    """Construct a single named backend (no availability check)."""
    if name == "extractive":
        return ExtractiveAnswerer()
    if name == "ollama":
        return OllamaAnswerer(
            model=opts.get("ollama_model", "llama3.2"),
            url=opts.get("ollama_url"),
        )
    if name == "llama-cpp":
        return LlamaCppAnswerer(model_path=opts.get("model_path"))
    if name == "claude":
        return ClaudeAnswerer(model=opts.get("model", DEFAULT_CLAUDE_MODEL))
    raise ValueError(f"unknown backend: {name!r}")


def resolve_backend(name: str = "auto", **opts) -> Answerer:
    """Return a ready-to-use backend.

    ``auto`` returns the first *available* offline backend, guaranteeing the
    system works disconnected. A named backend is returned as-is (its
    availability is the caller's concern).
    """
    if name != "auto":
        return make_backend(name, **opts)

    for candidate in _AUTO_ORDER:
        backend = make_backend(candidate, **opts)
        if backend.available():
            return backend
    return ExtractiveAnswerer()  # always-on fallback
