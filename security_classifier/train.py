"""Train and evaluate the defensive malicious-Python-code classifier.

Usage:
    python -m security_classifier.train
    python -m security_classifier.train --benign-dir data/security/benign/falconpy
    python -m security_classifier.train --benign-dir ... --malicious-dir ...

Without ``--benign-dir`` / ``--malicious-dir``, a small synthetic placeholder
set fills in that class (see ``dataset.py``) so the command always runs.
Metrics are only meaningful once real, representative data is supplied on
both sides.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from .dataset import build_dataset
from .features import FEATURE_NAMES

DEFAULT_MODEL_PATH = "security_classifier.model.joblib"


def train(
    benign_dir: Optional[str],
    malicious_dir: Optional[str],
    model_path: str = DEFAULT_MODEL_PATH,
) -> None:
    try:
        import joblib
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report, confusion_matrix
        from sklearn.model_selection import train_test_split
    except ImportError:
        print(
            "error: this command needs scikit-learn and joblib.\n"
            "  pip install scikit-learn joblib",
            file=sys.stderr,
        )
        sys.exit(1)

    if not benign_dir or not malicious_dir:
        print(
            "[warning] using synthetic placeholder data for the class(es) "
            "with no --*-dir supplied. This exercises the pipeline but is "
            "NOT a meaningful real-world classifier. See dataset.py.",
            file=sys.stderr,
        )

    xs, ys = build_dataset(benign_dir, malicious_dir)

    if len(set(ys)) < 2:
        print("error: need both benign and malicious samples to train.", file=sys.stderr)
        sys.exit(1)

    stratify = ys if len(ys) >= 8 else None
    x_train, x_test, y_train, y_test = train_test_split(
        xs, ys, test_size=0.25, random_state=0, stratify=stratify
    )

    clf = RandomForestClassifier(n_estimators=200, random_state=0, class_weight="balanced")
    clf.fit(x_train, y_train)

    y_pred = clf.predict(x_test)
    print(classification_report(y_test, y_pred, target_names=["benign", "malicious"]))
    print("Confusion matrix (rows=true, cols=pred):")
    print(confusion_matrix(y_test, y_pred))

    importances = sorted(zip(FEATURE_NAMES, clf.feature_importances_), key=lambda t: -t[1])
    print("\nTop features:")
    for name, importance in importances[:6]:
        print(f"  {name:28s} {importance:.3f}")

    joblib.dump(clf, model_path)
    print(f"\nSaved model -> {model_path}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benign-dir", default=None, help="directory of real benign .py files")
    parser.add_argument("--malicious-dir", default=None, help="directory of real malicious .py files")
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH)
    args = parser.parse_args(argv)
    train(args.benign_dir, args.malicious_dir, args.model_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
