"""A logistic-regression risk indicator over the ISO 27799 audit results.

Turns the per-control pass/fail results from ``audit.run_audit`` into one
severity-weighted risk fraction per control domain (only domains with at
least one *automated* control produce a signal -- manual-review controls
always read as "pending" regardless of the organization, so they carry no
discriminating information for this model), then fits a logistic-regression
classifier to those domain-risk vectors.

The training set (``build_dataset``) is a small, HAND-AUTHORED, SYNTHETIC set
of domain-risk vectors with illustrative "high incident risk" / "low incident
risk" labels -- there is no real incident/breach history behind it. Treat the
output the same way ``security_classifier`` asks you to treat its synthetic
placeholder model: a runnable methodology demonstration of "logistic
regression over audit-derived features", not a real-world calibrated
probability. A real risk model needs real, labeled incident history.

Usage:
    python -m pacs_iso27799_audit.risk_model --config sample_config.json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List, Tuple

from .audit import Result, run_audit
from .controls import CONTROLS, DOMAINS

SEVERITY_WEIGHT = {"high": 3.0, "medium": 2.0, "low": 1.0}

# Only domains that contain at least one automated control produce a varying
# signal -- manual controls always report "manual_review" here regardless of
# the input config, so including them would just add a constant, uninformative
# feature.
RISK_DOMAINS: List[int] = sorted({c.domain for c in CONTROLS if c.check_type == "automated"})
FEATURE_NAMES: List[str] = [f"domain_{d}_risk" for d in RISK_DOMAINS]

DISCLAIMER = (
    "This risk indicator is a logistic-regression model trained ONLY on a small, "
    "hand-authored SYNTHETIC dataset -- not on real incident or breach history. "
    "Treat it as a methodology demonstration, not a calibrated probability. A "
    "real risk model needs real, representative, labeled incident data."
)


def domain_risk(results: List[Result], domain_num: int) -> float:
    """Severity-weighted fraction of automated controls in this domain that
    failed (missing config data counts as half-weight, since "we don't know"
    is itself a partial risk signal). Returns 0.0 if the domain has no
    automated controls to score.
    """
    relevant = [r for r in results if r.control.domain == domain_num and r.control.check_type == "automated"]
    if not relevant:
        return 0.0
    weight_sum = sum(SEVERITY_WEIGHT[r.control.severity] for r in relevant)
    risk = 0.0
    for r in relevant:
        w = SEVERITY_WEIGHT[r.control.severity]
        if r.status == "fail":
            risk += w
        elif r.status == "missing_data":
            risk += 0.5 * w
    return risk / weight_sum


def features_from_results(results: List[Result]) -> List[float]:
    return [domain_risk(results, d) for d in RISK_DOMAINS]


def _risk_vector(overrides: Dict[int, float] = None, baseline: float = 0.1) -> List[float]:
    values = {d: baseline for d in RISK_DOMAINS}
    values.update(overrides or {})
    return [values[d] for d in RISK_DOMAINS]


def _synthetic_high_risk_samples() -> List[Tuple[List[float], int]]:
    # Domain numbers used below: 9=Access control, 10=Cryptography,
    # 12=Operations security, 13=Communications, 14=Acquisition/dev,
    # 15=Supplier relationships, 17=Business continuity, 18=Compliance.
    return [
        (_risk_vector({9: 0.9, 10: 0.8, 12: 0.85}), 1),
        (_risk_vector({9: 0.7, 12: 0.9, 13: 0.6}), 1),
        (_risk_vector({9: 0.95, 10: 0.9}), 1),
        (_risk_vector({12: 0.9, 17: 0.8, 18: 0.7}), 1),
        (_risk_vector({9: 0.8, 14: 0.7, 15: 0.8}), 1),
        (_risk_vector({9: 0.85, 10: 0.7, 12: 0.8, 13: 0.75}), 1),
        (_risk_vector({9: 1.0, 12: 1.0, 17: 0.9}), 1),
        (_risk_vector({10: 0.9, 12: 0.85, 18: 0.6}), 1),
    ]


def _synthetic_low_risk_samples() -> List[Tuple[List[float], int]]:
    return [
        (_risk_vector({}), 0),
        (_risk_vector({6: 0.2}), 0),
        (_risk_vector({7: 0.15, 15: 0.2}), 0),
        (_risk_vector({9: 0.15, 10: 0.1}), 0),
        (_risk_vector({12: 0.2, 17: 0.1}), 0),
        (_risk_vector({18: 0.15}), 0),
        (_risk_vector({}, baseline=0.05), 0),
        (_risk_vector({9: 0.1, 12: 0.1, 13: 0.1}), 0),
    ]


def build_dataset() -> Tuple[List[List[float]], List[int]]:
    samples = _synthetic_high_risk_samples() + _synthetic_low_risk_samples()
    xs = [s[0] for s in samples]
    ys = [s[1] for s in samples]
    return xs, ys


def fit_model():
    try:
        from sklearn.linear_model import LogisticRegression
    except ImportError:
        print("error: this command needs scikit-learn.\n  pip install scikit-learn", file=sys.stderr)
        sys.exit(1)

    xs, ys = build_dataset()
    model = LogisticRegression(max_iter=1000)
    model.fit(xs, ys)
    return model


def score(results: List[Result]) -> Tuple[float, "object"]:
    """Returns (predicted_probability_of_high_risk, fitted_model)."""
    model = fit_model()
    x = features_from_results(results)
    proba = model.predict_proba([x])[0][1]
    return float(proba), model


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, help="Path to a deployment config JSON file")
    args = parser.parse_args(argv)

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    results = run_audit(config)
    proba, model = score(results)

    print(DISCLAIMER, file=sys.stderr)
    print()
    print(f"Estimated risk indicator: {proba:.2f}  (0=low risk pattern, 1=high risk pattern,")
    print("                           relative to the synthetic training set only)")
    print()
    print("Domain risk inputs (severity-weighted fail fraction, 0=all pass, 1=all fail):")
    for d in RISK_DOMAINS:
        print(f"  Domain {d:2d} ({DOMAINS[d]}): {domain_risk(results, d):.2f}")
    print()
    print("Logistic regression coefficients (this synthetic model only, sorted by |weight|):")
    for name, coef in sorted(zip(FEATURE_NAMES, model.coef_[0]), key=lambda t: -abs(t[1])):
        print(f"  {name:20s} {coef:+.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
