#!/usr/bin/env python3
"""Offline CWE-informed information-security risk calculator.

Implements a Likelihood x Impact risk-scoring model aligned with the
methodology described in ISO/IEC 27005 and referenced by ISO/IEC 27001
clause 6.1.2 (risk assessment) -- see ../06-yisum-maasi.md in this book.

Fully offline: the CWE baseline table below is a small, hand-curated
snapshot (not the live MITRE CWE database) covering commonly-cited
weaknesses (broadly informed by recurring entries in the CWE Top 25 "Most
Dangerous Software Weaknesses" lists). It is a *starting point* only -- a
risk owner must review and calibrate likelihood/impact to their own
environment before using the output to justify risk-treatment decisions in
a real Statement of Applicability (SoA). No network access is used or
required.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Baseline CWE table: id -> (name, category, likelihood 1-5,
#                            impact_confidentiality, impact_integrity,
#                            impact_availability), each impact 1-5.
# These are illustrative defaults, not measured facts about any system.
# ---------------------------------------------------------------------------
CWE_BASELINE: dict[str, dict] = {
    "CWE-79": {"name": "Cross-Site Scripting (XSS)", "category": "Web / קלט משתמש",
               "likelihood": 4, "impact_c": 3, "impact_i": 3, "impact_a": 1},
    "CWE-89": {"name": "SQL Injection", "category": "Web / קלט משתמש",
               "likelihood": 4, "impact_c": 5, "impact_i": 5, "impact_a": 4},
    "CWE-78": {"name": "OS Command Injection", "category": "Web / קלט משתמש",
               "likelihood": 3, "impact_c": 5, "impact_i": 5, "impact_a": 5},
    "CWE-94": {"name": "Code Injection", "category": "Web / קלט משתמש",
               "likelihood": 3, "impact_c": 5, "impact_i": 5, "impact_a": 5},
    "CWE-22": {"name": "Path Traversal", "category": "Web / קלט משתמש",
               "likelihood": 4, "impact_c": 4, "impact_i": 3, "impact_a": 2},
    "CWE-352": {"name": "Cross-Site Request Forgery (CSRF)", "category": "Web / הרשאות",
                "likelihood": 3, "impact_c": 2, "impact_i": 4, "impact_a": 1},
    "CWE-434": {"name": "Unrestricted Upload of Dangerous File Type", "category": "Web / קלט משתמש",
                "likelihood": 3, "impact_c": 4, "impact_i": 5, "impact_a": 4},
    "CWE-502": {"name": "Deserialization of Untrusted Data", "category": "Web / קלט משתמש",
                "likelihood": 2, "impact_c": 5, "impact_i": 5, "impact_a": 4},
    "CWE-611": {"name": "Improper Restriction of XML External Entity Reference (XXE)",
                "category": "Web / קלט משתמש",
                "likelihood": 2, "impact_c": 5, "impact_i": 3, "impact_a": 3},
    "CWE-287": {"name": "Improper Authentication", "category": "זהות והרשאות",
                "likelihood": 4, "impact_c": 4, "impact_i": 4, "impact_a": 2},
    "CWE-306": {"name": "Missing Authentication for Critical Function", "category": "זהות והרשאות",
                "likelihood": 3, "impact_c": 5, "impact_i": 5, "impact_a": 4},
    "CWE-862": {"name": "Missing Authorization", "category": "זהות והרשאות",
                "likelihood": 4, "impact_c": 4, "impact_i": 4, "impact_a": 2},
    "CWE-863": {"name": "Incorrect Authorization", "category": "זהות והרשאות",
                "likelihood": 3, "impact_c": 4, "impact_i": 4, "impact_a": 2},
    "CWE-269": {"name": "Improper Privilege Management", "category": "זהות והרשאות",
                "likelihood": 3, "impact_c": 4, "impact_i": 5, "impact_a": 3},
    "CWE-798": {"name": "Use of Hard-coded Credentials", "category": "ניהול סודות",
                "likelihood": 3, "impact_c": 5, "impact_i": 4, "impact_a": 2},
    "CWE-321": {"name": "Use of Hard-coded Cryptographic Key", "category": "ניהול סודות",
                "likelihood": 2, "impact_c": 5, "impact_i": 4, "impact_a": 1},
    "CWE-522": {"name": "Insufficiently Protected Credentials", "category": "ניהול סודות",
                "likelihood": 3, "impact_c": 5, "impact_i": 3, "impact_a": 1},
    "CWE-259": {"name": "Use of Hard-coded Password", "category": "ניהול סודות",
                "likelihood": 3, "impact_c": 5, "impact_i": 4, "impact_a": 2},
    "CWE-200": {"name": "Exposure of Sensitive Information to an Unauthorized Actor",
                "category": "חשיפת מידע",
                "likelihood": 4, "impact_c": 4, "impact_i": 1, "impact_a": 1},
    "CWE-209": {"name": "Generation of Error Message Containing Sensitive Information",
                "category": "חשיפת מידע",
                "likelihood": 4, "impact_c": 2, "impact_i": 1, "impact_a": 1},
    "CWE-732": {"name": "Incorrect Permission Assignment for Critical Resource",
                "category": "תצורה",
                "likelihood": 3, "impact_c": 4, "impact_i": 4, "impact_a": 3},
    "CWE-284": {"name": "Improper Access Control", "category": "זהות והרשאות",
                "likelihood": 4, "impact_c": 4, "impact_i": 4, "impact_a": 3},
    "CWE-190": {"name": "Integer Overflow or Wraparound", "category": "לוגיקה / זיכרון",
                "likelihood": 2, "impact_c": 2, "impact_i": 3, "impact_a": 3},
    "CWE-125": {"name": "Out-of-bounds Read", "category": "לוגיקה / זיכרון",
                "likelihood": 3, "impact_c": 4, "impact_i": 1, "impact_a": 3},
    "CWE-787": {"name": "Out-of-bounds Write", "category": "לוגיקה / זיכרון",
                "likelihood": 3, "impact_c": 4, "impact_i": 5, "impact_a": 4},
    "CWE-416": {"name": "Use After Free", "category": "לוגיקה / זיכרון",
                "likelihood": 2, "impact_c": 4, "impact_i": 4, "impact_a": 4},
    "CWE-476": {"name": "NULL Pointer Dereference", "category": "לוגיקה / זיכרון",
                "likelihood": 3, "impact_c": 1, "impact_i": 1, "impact_a": 4},
    "CWE-311": {"name": "Missing Encryption of Sensitive Data", "category": "הצפנה",
                "likelihood": 3, "impact_c": 5, "impact_i": 2, "impact_a": 1},
    "CWE-327": {"name": "Use of a Broken or Risky Cryptographic Algorithm", "category": "הצפנה",
                "likelihood": 2, "impact_c": 4, "impact_i": 3, "impact_a": 1},
    "CWE-330": {"name": "Use of Insufficiently Random Values", "category": "הצפנה",
                "likelihood": 2, "impact_c": 3, "impact_i": 3, "impact_a": 1},
    "CWE-918": {"name": "Server-Side Request Forgery (SSRF)", "category": "Web / רשת",
                "likelihood": 3, "impact_c": 4, "impact_i": 3, "impact_a": 3},
    "CWE-400": {"name": "Uncontrolled Resource Consumption", "category": "זמינות",
                "likelihood": 3, "impact_c": 1, "impact_i": 1, "impact_a": 5},
    "CWE-668": {"name": "Exposure of Resource to Wrong Sphere", "category": "תצורה",
                "likelihood": 3, "impact_c": 3, "impact_i": 3, "impact_a": 2},
    "CWE-1188": {"name": "Insecure Default Initialization of Resource", "category": "תצורה",
                 "likelihood": 3, "impact_c": 3, "impact_i": 3, "impact_a": 2},
    "CWE-20": {"name": "Improper Input Validation", "category": "קלט משתמש",
               "likelihood": 4, "impact_c": 3, "impact_i": 3, "impact_a": 2},
}

RISK_LEVELS = (
    (1, 4, "נמוך (Low)"),
    (5, 9, "בינוני (Medium)"),
    (10, 16, "גבוה (High)"),
    (17, 25, "קריטי (Critical)"),
)


def risk_level(score: int) -> str:
    for lo, hi, label in RISK_LEVELS:
        if lo <= score <= hi:
            return label
    return "לא ידוע"


def compute_score(likelihood: int, impact: int) -> int:
    """5x5 likelihood x impact matrix, per ISO/IEC 27005-style scoring."""
    for value, name in ((likelihood, "likelihood"), (impact, "impact")):
        if not 1 <= value <= 5:
            raise ValueError(f"{name} must be between 1 and 5, got {value}")
    return likelihood * impact


@dataclass
class Finding:
    cwe_id: str
    asset: str = ""
    likelihood: int | None = None
    impact_c: int | None = None
    impact_i: int | None = None
    impact_a: int | None = None
    notes: str = ""

    def resolve(self) -> dict:
        """Merge explicit overrides with the CWE baseline (baseline is the fallback)."""
        baseline = CWE_BASELINE.get(self.cwe_id.upper())
        if baseline is None:
            raise KeyError(
                f"{self.cwe_id} אינו ברשימת ה-CWE הבסיסית של הכלי. "
                "השתמשו ב--likelihood/--impact-c/--impact-i/--impact-a כדי לספק ערכים ידנית."
            )
        likelihood = self.likelihood if self.likelihood is not None else baseline["likelihood"]
        impact_c = self.impact_c if self.impact_c is not None else baseline["impact_c"]
        impact_i = self.impact_i if self.impact_i is not None else baseline["impact_i"]
        impact_a = self.impact_a if self.impact_a is not None else baseline["impact_a"]
        impact = max(impact_c, impact_i, impact_a)
        score = compute_score(likelihood, impact)
        return {
            "cwe_id": self.cwe_id.upper(),
            "name": baseline["name"],
            "category": baseline["category"],
            "asset": self.asset,
            "likelihood": likelihood,
            "impact_c": impact_c,
            "impact_i": impact_i,
            "impact_a": impact_a,
            "impact_max": impact,
            "score": score,
            "risk_level": risk_level(score),
            "notes": self.notes,
        }


def load_findings(path: Path) -> list[Finding]:
    if path.suffix.lower() == ".json":
        rows = json.loads(path.read_text(encoding="utf-8"))
    elif path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
    else:
        raise ValueError("קובץ הממצאים חייב להיות .json או .csv")

    findings = []
    for row in rows:
        def _int(key):
            v = row.get(key)
            return int(v) if v not in (None, "") else None

        findings.append(Finding(
            cwe_id=row["cwe_id"],
            asset=row.get("asset", ""),
            likelihood=_int("likelihood"),
            impact_c=_int("impact_c"),
            impact_i=_int("impact_i"),
            impact_a=_int("impact_a"),
            notes=row.get("notes", ""),
        ))
    return findings


def print_table(rows: list[dict]) -> None:
    headers = ["cwe_id", "name", "asset", "likelihood", "impact_max", "score", "risk_level"]
    widths = {h: max(len(h), *(len(str(r.get(h, ""))) for r in rows)) if rows else len(h) for h in headers}
    print(" | ".join(h.ljust(widths[h]) for h in headers))
    print("-+-".join("-" * widths[h] for h in headers))
    for r in sorted(rows, key=lambda x: x["score"], reverse=True):
        print(" | ".join(str(r.get(h, "")).ljust(widths[h]) for h in headers))


def cmd_list(_args: argparse.Namespace) -> None:
    print(f"{'CWE':<10} {'קטגוריה':<20} {'שם':<55} {'Likelihood':<11} {'C':<2} {'I':<2} {'A':<2}")
    for cwe_id, data in sorted(CWE_BASELINE.items()):
        print(f"{cwe_id:<10} {data['category']:<20} {data['name']:<55} "
              f"{data['likelihood']:<11} {data['impact_c']:<2} {data['impact_i']:<2} {data['impact_a']:<2}")


def cmd_score(args: argparse.Namespace) -> None:
    finding = Finding(
        cwe_id=args.cwe,
        asset=args.asset or "",
        likelihood=args.likelihood,
        impact_c=args.impact_c,
        impact_i=args.impact_i,
        impact_a=args.impact_a,
        notes=args.notes or "",
    )
    result = finding.resolve()
    for key, value in result.items():
        print(f"{key:12}: {value}")


def cmd_report(args: argparse.Namespace) -> None:
    findings = load_findings(Path(args.input))
    rows = [f.resolve() for f in findings]
    print_table(rows)
    if args.output:
        out_path = Path(args.output)
        with out_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nרשומת הסיכונים נשמרה ל: {out_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="מחשבון סקר סיכונים (Likelihood x Impact) מבוסס CWE, "
                     "בהתאם למתודולוגיית ISO/IEC 27005 / ISO/IEC 27001 6.1.2. "
                     "פועל לחלוטין Offline.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="הצג את טבלת ה-CWE הבסיסית הכלולה בכלי")
    p_list.set_defaults(func=cmd_list)

    p_score = sub.add_parser("score", help="חשב ציון סיכון עבור CWE בודד")
    p_score.add_argument("--cwe", required=True, help="מזהה CWE, למשל CWE-89")
    p_score.add_argument("--asset", help="שם הנכס/המערכת המושפעת")
    p_score.add_argument("--likelihood", type=int, help="דריסת סבירות (1-5)")
    p_score.add_argument("--impact-c", type=int, help="דריסת השפעה על סודיות (1-5)")
    p_score.add_argument("--impact-i", type=int, help="דריסת השפעה על שלמות (1-5)")
    p_score.add_argument("--impact-a", type=int, help="דריסת השפעה על זמינות (1-5)")
    p_score.add_argument("--notes", help="הערות חופשיות")
    p_score.set_defaults(func=cmd_score)

    p_report = sub.add_parser("report", help="חשב רשומת סיכונים מקובץ ממצאים (JSON/CSV)")
    p_report.add_argument("--input", required=True, help="נתיב לקובץ ממצאים (.json או .csv)")
    p_report.add_argument("--output", help="נתיב אופציונלי לשמירת רשומת הסיכונים כ-CSV")
    p_report.set_defaults(func=cmd_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (KeyError, ValueError) as exc:
        print(f"שגיאה: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
