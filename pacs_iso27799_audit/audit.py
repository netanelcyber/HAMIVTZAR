"""Score a PACS deployment's documented configuration against the ISO
27799-aligned control catalog in ``controls.py``.

This is a **configuration-file** auditor, not a network scanner or
penetration-testing tool: it never opens a socket. You (or an authorized
assessor) describe the deployment in a JSON file -- see
``sample_config.json`` -- and this tool tells you which automatable controls
pass/fail and which controls need a human to answer from policy documents,
interviews, or a physical walkthrough.

Usage:
    python -m pacs_iso27799_audit.audit --config sample_config.json
    python -m pacs_iso27799_audit.audit --config my_deployment.json --output report.md
    python -m pacs_iso27799_audit.audit --list-controls
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .controls import CONTROLS, DOMAINS, Control

DISCLAIMER = (
    "This report reflects only the configuration values supplied in the input "
    "file. It is a documentation/config-review aid, not a certification and "
    "not a substitute for a qualified ISO 27799 assessor or a network "
    "penetration test authorized in writing by the system owner."
)


@dataclass
class Result:
    control: Control
    status: str  # "pass" | "fail" | "manual_review" | "missing_data"
    detail: str


def _get_nested(config: Dict[str, Any], dotted_path: str) -> Any:
    node: Any = config
    for key in dotted_path.split("."):
        if not isinstance(node, dict) or key not in node:
            return _MISSING
        node = node[key]
    return node


_MISSING = object()


def _check(operator: str, actual: Any, expected: Any) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "truthy":
        return bool(actual) is expected
    if operator == "le":
        return isinstance(actual, (int, float)) and actual <= expected
    if operator == "ge":
        return isinstance(actual, (int, float)) and actual >= expected
    raise ValueError(f"unknown operator: {operator}")


def evaluate_control(control: Control, config: Dict[str, Any]) -> Result:
    if control.check_type == "manual":
        return Result(
            control, "manual_review",
            f"Needs manual verification: {control.description}",
        )

    actual = _get_nested(config, control.config_path)
    if actual is _MISSING:
        return Result(
            control, "missing_data",
            f"Config key '{control.config_path}' not present in input file.",
        )

    passed = _check(control.operator, actual, control.expected)
    status = "pass" if passed else "fail"
    detail = f"value={actual!r} expected {control.operator} {control.expected!r}"
    return Result(control, status, detail)


def run_audit(config: Dict[str, Any], controls: List[Control] = CONTROLS) -> List[Result]:
    return [evaluate_control(c, config) for c in controls]


def summarize(results: List[Result]) -> Dict[str, int]:
    counts = {"pass": 0, "fail": 0, "manual_review": 0, "missing_data": 0}
    for r in results:
        counts[r.status] += 1
    return counts


_STATUS_LABEL = {
    "pass": "PASS",
    "fail": "FAIL",
    "manual_review": "MANUAL REVIEW",
    "missing_data": "NO DATA",
}


def render_markdown_report(results: List[Result], title: str) -> str:
    counts = summarize(results)
    lines = [f"# {title}", "", DISCLAIMER, "", "## Summary", ""]
    lines.append(
        f"- Automated PASS: {counts['pass']}\n"
        f"- Automated FAIL: {counts['fail']}\n"
        f"- Needs manual review: {counts['manual_review']}\n"
        f"- Missing config data: {counts['missing_data']}"
    )
    lines.append("")

    by_domain: Dict[int, List[Result]] = {}
    for r in results:
        by_domain.setdefault(r.control.domain, []).append(r)

    for domain_num in sorted(by_domain):
        lines.append(f"## Domain {domain_num}: {DOMAINS[domain_num]}")
        lines.append("")
        lines.append("| Control | Status | Severity | Detail |")
        lines.append("|---|---|---|---|")
        for r in by_domain[domain_num]:
            lines.append(
                f"| {r.control.id} — {r.control.title} | {_STATUS_LABEL[r.status]} "
                f"| {r.control.severity} | {r.detail} |"
            )
        lines.append("")

    failed_or_manual = [r for r in results if r.status in ("fail", "manual_review")]
    if failed_or_manual:
        lines.append("## Remediation guidance")
        lines.append("")
        for r in failed_or_manual:
            lines.append(f"- **{r.control.id}** ({_STATUS_LABEL[r.status]}): {r.control.remediation}")
        lines.append("")

    return "\n".join(lines)


def print_console_report(results: List[Result]) -> None:
    counts = summarize(results)
    print(DISCLAIMER, file=sys.stderr)
    print()
    for r in results:
        print(f"[{_STATUS_LABEL[r.status]:14s}] {r.control.id:8s} {r.control.title}")
    print()
    print(
        f"pass={counts['pass']} fail={counts['fail']} "
        f"manual_review={counts['manual_review']} missing_data={counts['missing_data']}"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help="Path to a deployment config JSON file (see sample_config.json)")
    parser.add_argument("--output", help="Write a Markdown report to this path instead of only printing to stdout")
    parser.add_argument("--title", default="PACS ISO 27799 Compliance Audit", help="Report title")
    parser.add_argument("--list-controls", action="store_true", help="Print the control catalog and exit")
    args = parser.parse_args(argv)

    if args.list_controls:
        for c in CONTROLS:
            print(f"{c.id}\t[{c.check_type}]\tDomain {c.domain} ({DOMAINS[c.domain]})\t{c.title}")
        return 0

    if not args.config:
        parser.error("--config is required unless --list-controls is given")

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    results = run_audit(config)
    print_console_report(results)

    if args.output:
        report = render_markdown_report(results, args.title)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nMarkdown report written to {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
