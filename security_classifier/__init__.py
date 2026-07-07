"""A defensive, static-analysis classifier for Python source code.

Flags structurally suspicious Python files (suspicious imports, dynamic
execution, obfuscation indicators, network/persistence patterns) using
interpretable engineered features — never by executing the analyzed code.

Data sourcing, deliberately:

* **Benign class** — real Python source you point this at, e.g. a local clone
  of a legitimate, permissively-licensed security-vendor SDK such as
  CrowdStrike FalconPy (see ``scripts/fetch_benign_corpus.py``, which you run
  yourself; nothing here fetches or clones anything automatically).
* **Malicious class** — must be real samples *you* supply in an isolated
  directory. Until you do, a small hand-authored set of synthetic feature
  vectors (not source code, not derived from real or functional attack code)
  stands in so the pipeline is runnable end to end. See ``dataset.py``.

This module intentionally does not include, fetch, or train on offensive
tooling (exploitation frameworks, autonomous pentesting agents) or
unvetted/scraped "attack code" — only structural pattern recognition over
labeled data you provide.
"""

from .features import Features, FEATURE_NAMES, extract_features
from .dataset import build_dataset, load_labeled_directory, BENIGN, MALICIOUS

__all__ = [
    "Features",
    "FEATURE_NAMES",
    "extract_features",
    "build_dataset",
    "load_labeled_directory",
    "BENIGN",
    "MALICIOUS",
]
