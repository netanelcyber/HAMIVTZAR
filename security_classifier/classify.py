"""Score Python files as benign/malicious with a trained classifier.

Usage:
    python -m security_classifier.classify path/to/file_or_dir
    python -m security_classifier.classify path/to/file.py --model-path custom.joblib
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterator

from .features import extract_features
from .train import DEFAULT_MODEL_PATH


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

    clf = joblib.load(args.model_path)

    for path in _iter_targets(args.target):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
        vector = extract_features(source).to_vector()
        proba = clf.predict_proba([vector])[0]
        malicious_score = proba[1] if len(proba) > 1 else 0.0
        label = "MALICIOUS" if malicious_score >= 0.5 else "benign"
        print(f"{malicious_score:5.2f}  {label:9s}  {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
