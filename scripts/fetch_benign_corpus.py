#!/usr/bin/env python3
"""Fetch legitimate, public security-vendor SDKs as benign training data for
the malicious-code classifier in ``security_classifier/``.

This script does nothing on its own — it only runs when YOU invoke it
locally, and it just shells out to ``git clone`` for each entry in SOURCES
below. Nothing in this project clones or scrapes anything automatically.

Usage:
    python scripts/fetch_benign_corpus.py
    python scripts/fetch_benign_corpus.py --dest data/security/benign
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import List, Tuple

# Legitimate, officially maintained, permissively-licensed security-vendor
# SDKs and API clients. Add more the same way (name, git URL) -- keep this
# list to vendor-maintained API clients / defensive tooling, not exploitation
# or offensive frameworks.
SOURCES: List[Tuple[str, str]] = [
    ("falconpy", "https://github.com/CrowdStrike/falconpy.git"),
    # ("pymisp", "https://github.com/MISP/PyMISP.git"),
    # ("splunk-sdk-python", "https://github.com/splunk/splunk-sdk-python.git"),
]


def fetch(dest_root: str) -> None:
    os.makedirs(dest_root, exist_ok=True)
    for name, url in SOURCES:
        target = os.path.join(dest_root, name)
        if os.path.exists(target):
            print(f"skip {name}: already present at {target}")
            continue
        print(f"cloning {name} <- {url}")
        subprocess.run(["git", "clone", "--depth", "1", url, target], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", default="data/security/benign")
    args = parser.parse_args()
    try:
        fetch(args.dest)
    except subprocess.CalledProcessError as exc:
        print(f"error: git clone failed ({exc})", file=sys.stderr)
        return 1
    print(f"\nDone. Train with:\n  python -m security_classifier.train --benign-dir {args.dest}/falconpy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
