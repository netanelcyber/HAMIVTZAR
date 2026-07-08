"""Summarize, in natural language, what a scanned Python file appears to do.

Takes the structural features + classifier score for one file (whether the
verdict is benign or malicious) and produces a plain-language summary of the
code's apparent behavior and why it scored the way it did.

Offline-first, exactly like ``linux_docs_llm.backends``: ``auto`` tries a
local LLM (Ollama, then llama.cpp) and always falls back to a deterministic,
dependency-free template — so this produces a natural-language summary even
fully disconnected. Claude is opt-in only (``--backend claude``) and is never
selected by ``auto``. Backend selection reuses
``linux_docs_llm.backends.resolve_backend`` rather than re-implementing the
Ollama -> llama.cpp -> Claude ordering here — see :func:`resolve_explain_backend`.

The model is never shown the raw source code — only the numeric/boolean
feature values already extracted by :mod:`security_classifier.features`. It
summarizes structure (imports, calls, indicators), not arbitrary file
content.
"""

from __future__ import annotations

import os
import sys
from typing import Callable, Optional

from linux_docs_llm.backends import ModelBackedAnswerer, resolve_backend

from .dynamic_features import DynamicFeatures
from .features import Features

OnText = Optional[Callable[[str], None]]

EXPLAIN_SYSTEM_PROMPT = """\
You are a security analyst assistant. You will be given the structural \
features and probability score a static-analysis classifier computed for one \
Python file -- never the raw source itself -- and, if available, a summary of \
its OBSERVED runtime behavior from a sandboxed dynamic trace (network \
connections, file writes, processes spawned). Summarize, in plain language for \
a non-expert, what the code most likely does and whether that looks benign or \
malicious.

Rules:
- Base everything ONLY on the feature/trace values given. Do not invent \
behavior they don't support, and do not claim to have seen the actual source.
- If a dynamic trace is present, treat observed behavior as stronger evidence \
than static structure alone -- an actual outbound connection or a write to an \
autostart location, if observed, is more meaningful than a structural hint.
- State plainly whether this looks more benign or more suspicious, citing the \
specific evidence that drove that call.
- If the signal is weak, mixed, or no dynamic trace was available, say so — \
do not overstate confidence.
- Keep it to 3-5 sentences. No headers, no bullet lists.\
"""


def resolve_explain_backend(name: str = "auto", **opts) -> Optional[ModelBackedAnswerer]:
    """Resolve the backend to use for ``--explain``, once per run (not per file).

    Reuses ``linux_docs_llm.backends.resolve_backend`` / ``make_backend``
    instead of re-implementing the Ollama -> llama.cpp -> Claude selection.
    Callers should resolve this ONCE and reuse the same engine across every
    file in a scan -- probing a local daemon, or loading a GGUF model, once
    per run rather than once per file.

    Returns ``None`` (meaning: use the deterministic, dependency-free offline
    template) for ``name == "template"``, or when nothing else is available.
    An explicitly-named backend (``ollama``/``llama-cpp``/``claude``) that
    turns out to be unavailable prints a warning before falling back --
    ``auto`` stays silent about intermediate misses, since trying each
    candidate and moving on is its whole point.
    """
    if name == "template":
        return None

    backend = resolve_backend(name, **opts)
    if isinstance(backend, ModelBackedAnswerer) and backend.available():
        return backend

    if name != "auto":
        print(f"[explain] {name} backend unavailable, using offline template", file=sys.stderr)
    return None


def _build_user_message(
    path: str,
    features: Features,
    score: float,
    dynamic: Optional[DynamicFeatures] = None,
) -> str:
    lines = [f"File: {path}", f"Classifier score (P[malicious]): {score:.2f}", "", "Static features:"]
    for name, value in features.to_dict().items():
        lines.append(f"  {name}: {value}")
    if dynamic is not None:
        lines.append("")
        lines.append("Observed runtime behavior (from a sandboxed trace):")
        for name, value in dynamic.to_dict().items():
            lines.append(f"  {name}: {value}")
    else:
        lines.append("")
        lines.append("No dynamic trace was provided -- this is static analysis only.")
    return "\n".join(lines)


_INDICATOR_LABELS = {
    "has_eval_exec": "dynamically executing code (eval/exec/compile)",
    "has_subprocess_shell_true": "running a shell command via subprocess",
    "has_os_system": "running a shell command via os.system",
    "has_base64_decode": "decoding a base64-encoded payload",
    "has_network_connect": "opening a network connection",
    "has_persistence_hint": "referencing an autostart/persistence location",
}


def _dynamic_sentence(dynamic: Optional[DynamicFeatures]) -> str:
    if dynamic is None:
        return "No sandboxed dynamic trace was provided, so this is static analysis only."
    d = dynamic.to_dict()
    observed = []
    if d["num_network_connections"]:
        observed.append(
            f"{int(d['num_network_connections'])} outbound network connection(s) "
            f"to {int(d['unique_remote_hosts'])} host(s)"
        )
    if d["num_persistence_writes"]:
        observed.append(f"{int(d['num_persistence_writes'])} write(s) to an autostart/persistence location")
    if d["num_files_written"]:
        observed.append(f"{int(d['num_files_written'])} file write(s) overall")
    if d["num_subprocess_spawned"]:
        observed.append(f"{int(d['num_subprocess_spawned'])} subprocess(es) spawned")
    if observed:
        return "In the sandboxed trace, it actually " + "; ".join(observed) + "."
    return "In the sandboxed trace it ran without any observed network, file-write, or subprocess activity."


def _template_summary(
    path: str,
    features: Features,
    score: float,
    dynamic: Optional[DynamicFeatures] = None,
) -> str:
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
    sentence4 = _dynamic_sentence(dynamic)
    return " ".join([sentence1, sentence2, sentence3, sentence4])


def summarize(
    path: str,
    features: Features,
    score: float,
    dynamic: Optional[DynamicFeatures] = None,
    engine: Optional[ModelBackedAnswerer] = None,
    on_text: OnText = None,
) -> str:
    """Return a natural-language summary of one classifier finding.

    ``dynamic``, if given, is the parsed output of a sandboxed runtime trace
    (see ``security_classifier.dynamic_features`` and
    ``scripts/sandboxed_trace.sh``) -- collected on the caller's own isolated
    infrastructure, never executed by this function.

    ``engine``, if given, is a backend resolved once via
    :func:`resolve_explain_backend` and reused across every file being
    scanned. ``None`` forces the offline, dependency-free template.
    """
    user_message = _build_user_message(path, features, score, dynamic)

    if engine is not None:
        return engine.generate(EXPLAIN_SYSTEM_PROMPT, user_message, on_text)

    text = _template_summary(path, features, score, dynamic)
    if on_text:
        on_text(text)
    return text
