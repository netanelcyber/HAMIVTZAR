"""Summarize, in natural language, what a scanned Python file appears to do.

Takes the structural features + classifier score for one file (whether the
verdict is benign or malicious) and produces a plain-language summary of the
code's apparent behavior and why it scored the way it did.

Offline-first, exactly like ``linux_docs_llm.backends``: ``auto`` tries a
local LLM (Ollama, then llama.cpp) and always falls back to a deterministic,
dependency-free template — so this produces a natural-language summary even
fully disconnected. Claude is opt-in only (``--backend claude``) and is never
selected by ``auto``.

The model is never shown the raw source code — only the numeric/boolean
feature values already extracted by :mod:`security_classifier.features`. It
summarizes structure (imports, calls, indicators), not arbitrary file
content.
"""

from __future__ import annotations

import os
import sys
from typing import Callable, Optional

from linux_docs_llm.backends import (
    DEFAULT_CLAUDE_MODEL,
    ClaudeAnswerer,
    LlamaCppAnswerer,
    OllamaAnswerer,
)

from .features import Features

OnText = Optional[Callable[[str], None]]

EXPLAIN_SYSTEM_PROMPT = """\
You are a security analyst assistant. You will be given the structural \
features and probability score a static-analysis classifier computed for one \
Python file — never the raw source itself. Summarize, in plain language for a \
non-expert, what the code most likely does structurally and whether that \
looks benign or malicious.

Rules:
- Base everything ONLY on the feature values given. Do not invent behavior \
the features don't support, and do not claim to have seen the actual source.
- State plainly whether this looks more benign or more suspicious, citing the \
specific features that drove that call.
- If the signal is weak or mixed, say so — do not overstate confidence.
- Keep it to 3-5 sentences. No headers, no bullet lists.\
"""


def _build_user_message(path: str, features: Features, score: float) -> str:
    lines = [f"File: {path}", f"Classifier score (P[malicious]): {score:.2f}", "", "Features:"]
    for name, value in features.to_dict().items():
        lines.append(f"  {name}: {value}")
    return "\n".join(lines)


_INDICATOR_LABELS = {
    "has_eval_exec": "dynamically executing code (eval/exec/compile)",
    "has_subprocess_shell_true": "running a shell command via subprocess",
    "has_os_system": "running a shell command via os.system",
    "has_base64_decode": "decoding a base64-encoded payload",
    "has_network_connect": "opening a network connection",
    "has_persistence_hint": "referencing an autostart/persistence location",
}


def _template_summary(path: str, features: Features, score: float) -> str:
    """Deterministic, dependency-free natural-language summary. Always works."""
    d = features.to_dict()
    triggered = [_INDICATOR_LABELS[name] for name in _INDICATOR_LABELS if d.get(name)]

    verdict = "malicious" if score >= 0.5 else "benign"
    confidence = "strong" if abs(score - 0.5) > 0.3 else "weak"

    sentence1 = (
        f"{os.path.basename(path)} looks {verdict} to the classifier, "
        f"with {confidence} signal (score {score:.2f})."
    )
    if triggered:
        sentence2 = "Structurally, the code appears to be " + "; ".join(triggered) + "."
    else:
        sentence2 = (
            "No individual high-risk indicator was triggered; the score comes "
            "mostly from the file's overall size and import profile rather "
            "than any one dangerous call."
        )
    sentence3 = (
        f"It imports {d['num_imports']} module(s) ({d['suspicious_import_count']} "
        f"from the watched list) across {int(d['num_functions'])} function(s) and "
        f"{int(d['num_lines'])} lines."
    )
    if score < 0.5:
        sentence4 = "Overall this reads as ordinary application code rather than an attack pattern."
    else:
        sentence4 = (
            "The combination above is the kind of pattern static malware "
            "detectors flag for closer human review, not a confirmed verdict."
        )
    return " ".join([sentence1, sentence2, sentence3, sentence4])


def summarize(
    path: str,
    features: Features,
    score: float,
    backend: str = "auto",
    on_text: OnText = None,
    **backend_opts,
) -> str:
    """Return a natural-language summary of one classifier finding.

    ``backend`` follows the same names as ``linux_docs_llm``: ``auto`` (local
    LLM if available, else the offline template), ``ollama``, ``llama-cpp``,
    ``claude`` (online, opt-in), or ``template`` (force the offline fallback).
    """
    user_message = _build_user_message(path, features, score)

    engine = None
    if backend in ("auto", "ollama"):
        candidate = OllamaAnswerer(
            model=backend_opts.get("ollama_model", "llama3.2"),
            url=backend_opts.get("ollama_url"),
        )
        if candidate.available():
            engine = candidate
    if engine is None and backend in ("auto", "llama-cpp"):
        candidate = LlamaCppAnswerer(model_path=backend_opts.get("model_path"))
        if candidate.available():
            engine = candidate
    if engine is None and backend == "claude":
        candidate = ClaudeAnswerer(model=backend_opts.get("model") or DEFAULT_CLAUDE_MODEL)
        if candidate.available():
            engine = candidate
        else:
            print("[explain] claude backend unavailable, using offline template", file=sys.stderr)

    if engine is not None:
        return engine.generate(EXPLAIN_SYSTEM_PROMPT, user_message, on_text)

    text = _template_summary(path, features, score)
    if on_text:
        on_text(text)
    return text
