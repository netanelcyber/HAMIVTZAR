"""Build labeled feature datasets for the malicious-code classifier.

Benign samples come from real Python source files you point this at (e.g., a
local clone of a legitimate SDK such as CrowdStrike FalconPy — see
``scripts/fetch_benign_corpus.py``, which you run yourself). Malicious samples
must come from you too, via ``--malicious-dir`` pointing at real, isolated
samples. Until you have those, a small hand-authored set of SYNTHETIC feature
vectors stands in so the training pipeline is runnable end to end.

Those placeholder vectors are just numbers (import counts, boolean flags,
entropy scores) chosen to resemble typical malicious-signal combinations —
they are not extracted from, and do not contain, any real or functional
attack code.
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

from .features import Features

BENIGN = 0
MALICIOUS = 1

Sample = Tuple[List[float], int]


def _iter_python_files(directory: str):
    for dirpath, _dirnames, filenames in os.walk(directory):
        for name in filenames:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def load_labeled_directory(directory: str, label: int) -> List[Sample]:
    """Extract features for every ``.py`` file under ``directory``.

    Files are only ever parsed, never executed (see
    :func:`security_classifier.features.extract_features`).
    """
    from .features import extract_features  # local import avoids a cycle at import time

    samples: List[Sample] = []
    for path in _iter_python_files(directory):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
        samples.append((extract_features(source).to_vector(), label))
    return samples


def _vector(**overrides) -> List[float]:
    f = Features(num_lines=40, num_functions=2, num_imports=3)
    for key, value in overrides.items():
        setattr(f, key, value)
    return f.to_vector()


def _synthetic_malicious_samples() -> List[Sample]:
    return [
        (_vector(suspicious_import_count=3, has_eval_exec=1, has_base64_decode=1,
                 max_string_entropy=4.6, long_string_count=2), MALICIOUS),
        (_vector(suspicious_import_count=4, has_subprocess_shell_true=1,
                 has_network_connect=1, has_persistence_hint=1), MALICIOUS),
        (_vector(suspicious_import_count=2, has_os_system=1, has_network_connect=1,
                 max_string_entropy=4.2), MALICIOUS),
        (_vector(suspicious_import_count=5, has_eval_exec=1, has_base64_decode=1,
                 has_network_connect=1, max_string_entropy=5.0, long_string_count=4),
         MALICIOUS),
        (_vector(suspicious_import_count=3, has_persistence_hint=1,
                 has_subprocess_shell_true=1, has_os_system=1), MALICIOUS),
        (_vector(suspicious_import_count=4, has_eval_exec=1, has_persistence_hint=1,
                 max_string_entropy=4.8), MALICIOUS),
    ]


def _synthetic_benign_samples() -> List[Sample]:
    return [
        (_vector(num_lines=60, num_functions=4, num_imports=5), BENIGN),
        (_vector(num_lines=120, num_functions=8, num_imports=10), BENIGN),
        (_vector(num_lines=30, num_functions=2, num_imports=2,
                  suspicious_import_count=1), BENIGN),  # e.g. a single `os.path` use
        (_vector(num_lines=200, num_functions=15, num_imports=12), BENIGN),
        (_vector(num_lines=25, num_functions=1, num_imports=1,
                  long_string_count=1, max_string_entropy=3.0), BENIGN),  # a docstring
        (_vector(num_lines=80, num_functions=6, num_imports=6,
                  suspicious_import_count=2), BENIGN),  # e.g. `subprocess.run(..., shell=False)`
    ]


def build_dataset(
    benign_dir: Optional[str] = None,
    malicious_dir: Optional[str] = None,
) -> Tuple[List[List[float]], List[int]]:
    """Assemble ``(X, y)`` for training.

    Real files are used whenever a directory is given; otherwise a small
    synthetic placeholder set fills in that class (see module docstring) so
    the pipeline always runs end to end. Meaningful real-world accuracy
    requires supplying both directories with real, representative data.
    """
    samples: List[Sample] = []

    samples += load_labeled_directory(benign_dir, BENIGN) if benign_dir else _synthetic_benign_samples()
    samples += load_labeled_directory(malicious_dir, MALICIOUS) if malicious_dir else _synthetic_malicious_samples()

    xs = [s[0] for s in samples]
    ys = [s[1] for s in samples]
    return xs, ys
