"""Score Python files as benign/malicious with a trained classifier.

Usage:
    python -m security_classifier.classify path/to/file_or_dir
    python -m security_classifier.classify path/to/file.py --model-path custom.joblib

    # also summarize what each file appears to do, in natural language
    python -m security_classifier.classify path/to/file.py --explain
    python -m security_classifier.classify path/to/file.py --explain --explain-backend ollama

    # fold in a sandboxed runtime trace you collected yourself (see
    # scripts/sandboxed_trace.sh) -- only meaningful for a single file.
    # Observed behavior adjusts the printed score, not just the --explain text.
    python -m security_classifier.classify path/to/file.py --explain --trace trace.jsonl
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterator, Optional

from .dynamic_features import DynamicFeatures, dynamic_risk_boost
from .features import Features, extract_features
from .train import DEFAULT_MODEL_PATH

BACKEND_CHOICES = ["auto", "template", "ollama", "llama-cpp", "claude"]


def _iter_targets(path: str) -> Iterator[str]:
    if os.path.isfile(path):
        yield path
        return
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _score_file(clf, features: Features, dynamic: Optional[DynamicFeatures]) -> tuple[float, float]:
    """Return ``(combined_score, static_score)``.

    ``dynamic``, when present, adjusts the score via a transparent rule-based
    boost (see :func:`security_classifier.dynamic_features.dynamic_risk_boost`)
    -- observed behavior actually changes the verdict, not just the
    ``--explain`` narrative.
    """
    proba = clf.predict_proba([features.to_vector()])[0]
    static_score = proba[1] if len(proba) > 1 else 0.0
    combined_score = static_score
    if dynamic is not None:
        combined_score = min(1.0, static_score + dynamic_risk_boost(dynamic))
    return combined_score, static_score


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="a .py file or a directory to scan")
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH)
    parser.add_argument(
        "--trace",
        default=None,
        help=(
            "path to a JSON-Lines runtime trace collected on YOUR OWN isolated "
            "sandbox (see scripts/sandboxed_trace.sh) -- never collected by this "
            "command. Only meaningful when scanning a single file. Adjusts the "
            "printed score via a transparent rule-based boost, not just --explain."
        ),
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="also print a natural-language summary of what each file appears to do",
    )
    parser.add_argument(
        "--explain-backend",
        choices=BACKEND_CHOICES,
        default="auto",
        help="engine for --explain (default: auto -- local LLM if available, else an offline template)",
    )
    parser.add_argument("--ollama-model", default="llama3.2")
    parser.add_argument("--ollama-url", default=None)
    parser.add_argument("--llm-model-path", default=None, help="GGUF model path for --explain-backend llama-cpp")
    parser.add_argument("--claude-model", default=None, help="Claude model id for --explain-backend claude")
    args = parser.parse_args(argv)

    try:
        import joblib
    except ImportError:
        print("error: this command needs joblib.\n  pip install joblib", file=sys.stderr)
        return 1

    if not os.path.exists(args.model_path):
        print(
            f"error: model not found: {args.model_path}\n"
            f"Run `python -m security_classifier.train` first.",
            file=sys.stderr,
        )
        return 1

    if not os.path.exists(args.target):
        print(f"error: target not found: {args.target}", file=sys.stderr)
        return 1

    if args.trace and not os.path.isfile(args.target):
        print("error: --trace only applies when scanning a single file.", file=sys.stderr)
        return 1

    if args.trace and not os.path.exists(args.trace):
        print(f"error: trace file not found: {args.trace}", file=sys.stderr)
        return 1

    clf = joblib.load(args.model_path)

    dynamic = None
    if args.trace:
        from .dynamic_features import extract_dynamic_features, load_trace

        dynamic = extract_dynamic_features(load_trace(args.trace))

    # Resolve the --explain engine once per run, not once per file: probing a
    # local Ollama daemon or loading a GGUF model is expensive enough that
    # doing it per scanned file would be a serious slowdown on a directory.
    explain_engine = None
    if args.explain:
        from .explain import resolve_explain_backend

        explain_engine = resolve_explain_backend(
            args.explain_backend,
            ollama_model=args.ollama_model,
            ollama_url=args.ollama_url,
            model_path=args.llm_model_path,
            model=args.claude_model,
        )

    for path in _iter_targets(args.target):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
        features = extract_features(source)
        combined_score, static_score = _score_file(clf, features, dynamic)
        label = "MALICIOUS" if combined_score >= 0.5 else "benign"
        suffix = (
            f"  (static {static_score:.2f} + behavioral evidence)"
            if dynamic is not None and combined_score != static_score
            else ""
        )
        print(f"{combined_score:5.2f}  {label:9s}  {path}{suffix}")

        if args.explain:
            from .explain import summarize

            summary = summarize(path, features, combined_score, dynamic=dynamic, engine=explain_engine)
            print(f"        {summary}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
