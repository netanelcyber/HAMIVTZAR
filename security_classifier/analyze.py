"""Run an analytics report over the classifier's current training data.

Reports cross-validated per-sample scores, per-class score statistics, and
feature importances -- using real directories if given, or the synthetic
placeholder dataset from ``dataset.py`` otherwise. This command only reports
on data the pipeline already has; it never fetches or generates new code
samples.

Usage:
    python -m security_classifier.analyze
    python -m security_classifier.analyze --benign-dir data/security/benign/falconpy --malicious-dir path/to/real/samples
"""

from __future__ import annotations

import argparse
import statistics
import sys
from typing import Optional

from .dataset import BENIGN, MALICIOUS, build_dataset
from .features import FEATURE_NAMES


def analyze(benign_dir: Optional[str], malicious_dir: Optional[str]) -> None:
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_predict
    except ImportError:
        print(
            "error: this command needs scikit-learn.\n  pip install scikit-learn",
            file=sys.stderr,
        )
        sys.exit(1)

    if not benign_dir or not malicious_dir:
        print(
            "[warning] using synthetic placeholder data for the class(es) with "
            "no --*-dir supplied -- this reports on the pipeline's demo data, "
            "not real-world code. See dataset.py.",
            file=sys.stderr,
        )

    xs, ys = build_dataset(benign_dir, malicious_dir)
    n_benign, n_malicious = ys.count(BENIGN), ys.count(MALICIOUS)
    if n_benign < 2 or n_malicious < 2:
        print(
            "error: need at least 2 samples per class for cross-validated analytics.",
            file=sys.stderr,
        )
        sys.exit(1)

    clf = RandomForestClassifier(n_estimators=200, random_state=0, class_weight="balanced")

    # Cross-validated out-of-fold probabilities: every sample is scored by a
    # fold that did NOT train on it, so this isn't just memorized accuracy.
    n_splits = min(5, n_benign, n_malicious)
    proba = cross_val_predict(clf, xs, ys, cv=n_splits, method="predict_proba")
    scores = [p[1] for p in proba]  # P(malicious)

    print(f"Samples: {len(xs)}  (benign={n_benign}, malicious={n_malicious}, cv folds={n_splits})\n")

    print(f"{'#':>3}  {'true':10}  {'score':>6}  {'pred':10}")
    for i, (score, label) in enumerate(zip(scores, ys)):
        pred = "malicious" if score >= 0.5 else "benign"
        true = "malicious" if label == MALICIOUS else "benign"
        flag = "  <-- misclassified" if pred != true else ""
        print(f"{i:>3}  {true:10}  {score:6.2f}  {pred:10}{flag}")

    benign_scores = [s for s, y in zip(scores, ys) if y == BENIGN]
    malicious_scores = [s for s, y in zip(scores, ys) if y == MALICIOUS]

    print("\nScore statistics (cross-validated P(malicious)):")
    for label, group in [("benign", benign_scores), ("malicious", malicious_scores)]:
        print(
            f"  {label:10} mean={statistics.mean(group):.2f}  "
            f"min={min(group):.2f}  max={max(group):.2f}"
        )

    accuracy = sum(
        1 for s, y in zip(scores, ys) if (s >= 0.5) == (y == MALICIOUS)
    ) / len(ys)
    print(f"\nCross-validated accuracy: {accuracy:.0%}")

    # Fit once on everything for a global feature-importance summary (not
    # used for the per-sample scores above, which are cross-validated).
    clf.fit(xs, ys)
    importances = sorted(zip(FEATURE_NAMES, clf.feature_importances_), key=lambda t: -t[1])
    print("\nFeature importances:")
    for name, importance in importances:
        bar = "#" * int(importance * 40)
        print(f"  {name:28s} {importance:.3f}  {bar}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benign-dir", default=None, help="directory of real benign .py files")
    parser.add_argument("--malicious-dir", default=None, help="directory of real malicious .py files")
    args = parser.parse_args(argv)
    analyze(args.benign_dir, args.malicious_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
