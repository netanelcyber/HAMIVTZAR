"""Score Python files as benign/malicious with a trained classifier.

Usage:
    python -m security_classifier.classify path/to/file_or_dir
    python -m security_classifier.classify path/to/file.py --model-path custom.joblib

    # also summarize what each file appears to do, in natural language
    python -m security_classifier.classify path/to/file.py --explain
    python -m security_classifier.classify path/to/file.py --explain --explain-backend ollama

    # fold in a sandboxed runtime trace you collected yourself (see
    # scripts/sandboxed_trace.sh) -- only meaningful for a single file
    python -m security_classifier.classify path/to/file.py --explain --trace trace.jsonl
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterator, Optional

from .features import extract_features
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
            "command. Only meaningful when scanning a single file."
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

    for path in _iter_targets(args.target):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
        features = extract_features(source)
        proba = clf.predict_proba([features.to_vector()])[0]
        malicious_score = proba[1] if len(proba) > 1 else 0.0
        label = "MALICIOUS" if malicious_score >= 0.5 else "benign"
        print(f"{malicious_score:5.2f}  {label:9s}  {path}")

        if args.explain:
            from .explain import summarize

            summary = summarize(
                path,
                features,
                malicious_score,
                dynamic=dynamic,
                backend=args.explain_backend,
                ollama_model=args.ollama_model,
                ollama_url=args.ollama_url,
                model_path=args.llm_model_path,
                model=args.claude_model,
            )
            print(f"        {summary}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
