#!/usr/bin/env python3
"""Static triage helper for manually reviewing suspicious PHP, Python, or
JavaScript/TypeScript source (e.g. a file recovered from an upload-backdoor
finding like CWE-434 -- see book chapter 10).

This tool NEVER executes, imports, or evaluates the code it scans -- it only
reads each file as text and matches it against a curated set of regex
indicators (dynamic code execution, encoding/obfuscation chains, OS command
execution, common webshell/stager name strings, npm supply-chain install
hooks, long base64-like blobs). Every match is a **lead for a human analyst
to investigate**, not a verdict -- these are common, legitimate constructs
too (a backup script may legitimately call `system()`; a bundler may
legitimately call `eval()`). Treat the output as a triage checklist, the same
way you'd use `grep` for known-bad patterns before reading the file in full.

For deeper, ML-informed static analysis of Python specifically (AST-based
feature extraction, a trained classifier, natural-language explanations),
see security_classifier/ elsewhere in this repository -- this tool is the
lighter-weight, multi-language, regex-based companion to it, meant for quick
manual triage across PHP/Python/JS-TS rather than automated scoring.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SKIP_DIRS = {".git", "node_modules", "vendor", "__pycache__", ".venv", "venv"}

EXTENSION_LANGUAGE = {
    ".php": "php", ".phtml": "php", ".php3": "php", ".php4": "php", ".php5": "php",
    ".py": "python", ".pyw": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "javascript", ".tsx": "javascript",
}


@dataclass(frozen=True)
class Indicator:
    name: str
    pattern: "re.Pattern[str]"
    severity: str  # "High" | "Medium" | "Low"
    description: str


def _rx(pattern: str, flags: int = re.IGNORECASE) -> "re.Pattern[str]":
    return re.compile(pattern, flags)


# A long run of base64-alphabet characters is a weak but language-agnostic
# hint of an embedded encoded payload (webshells, stagers, obfuscated
# config blobs). 60 chars is short enough to catch small stagers, long
# enough to avoid flagging every UUID/hash in the file.
LONG_BASE64_BLOB = Indicator(
    "long-base64-like-blob", _rx(r"[A-Za-z0-9+/]{60,}={0,2}"), "Low",
    "מחרוזת ארוכה בפורמט base64 -- ייתכן payload מקודד; בדקו הקשר (עוגן לבדיקה, לא מסקנה)."
)

PHP_INDICATORS: list[Indicator] = [
    Indicator("eval-call", _rx(r"\beval\s*\("), "High",
              "eval() מפעיל מחרוזת כקוד PHP -- נקודת ריכוז קלאסית ל-webshells."),
    Indicator("assert-as-eval", _rx(r"\bassert\s*\(\s*['\"$]"), "High",
              "assert() עם מחרוזת/משתנה מתפקד כ-eval() נסתר בגרסאות PHP ישנות."),
    Indicator("create-function", _rx(r"\bcreate_function\s*\("), "High",
              "create_function() בונה ומריץ קוד מתוך מחרוזת -- דפוס webshell נפוץ."),
    Indicator("preg-replace-e-modifier", _rx(r"preg_replace\s*\([^)]*['\"]\s*/[a-z]*e[a-z]*['\"]"), "High",
              "מודיפייר /e ב-preg_replace() (PHP<5.5) מריץ את התחליף כקוד -- RCE ידוע."),
    Indicator("encode-decode-chain", _rx(r"(base64_decode|gzinflate|gzuncompress|str_rot13|convert_uuencode|hex2bin)\s*\("), "High",
              "שרשרת קידוד/פענוח נפוצה להסתרת payload (למשל eval(gzinflate(base64_decode(...))))."),
    Indicator("os-command-exec", _rx(r"\b(system|exec|shell_exec|passthru|popen|proc_open)\s*\("), "High",
              "קריאה להרצת פקודת מערכת הפעלה מתוך PHP."),
    Indicator("backtick-exec", _rx(r"`[^`]+`"), "Medium",
              "תחביר backticks ב-PHP מריץ פקודת shell (shell_exec מקוצר)."),
    Indicator("superglobal-to-sink", _rx(r"(eval|system|exec|shell_exec|passthru|assert)\s*\([^)]*\$_(GET|POST|REQUEST|COOKIE|SERVER)"), "High",
              "קלט משתמש ($_GET/$_POST/$_REQUEST) מוזן ישירות לפונקציית הרצה -- RCE סביר."),
    Indicator("extract-superglobal", _rx(r"\bextract\s*\(\s*\$_(GET|POST|REQUEST|COOKIE)"), "High",
              "extract() על superglobal יוצר משתנים שרירותיים מקלט משתמש."),
    Indicator("variable-variables", _rx(r"\$\$\w+"), "Medium",
              "משתני-משתנים ($$var) -- טכניקת ערפול נפוצה בקוד זדוני."),
    Indicator("file-write-from-request", _rx(r"(file_put_contents|fwrite|fputs)\s*\([^)]*\$_(GET|POST|REQUEST)"), "High",
              "כתיבת קובץ מתוך קלט משתמש ישיר -- דפוס התקנת/עדכון webshell."),
    Indicator("move-uploaded-file-loose", _rx(r"move_uploaded_file\s*\("), "Medium",
              "העלאת קובץ -- בדקו שיש אימות סיומת/תוכן קפדני בסביבתה (ראו CWE-434, פרק 10)."),
    Indicator("suppressed-errors-persistence", _rx(r"@?ini_set\s*\(\s*['\"]display_errors|error_reporting\s*\(\s*0\s*\)"), "Low",
              "השתקת שגיאות -- לעיתים משמשת להסתרת קוד זדוני משגיאות גלויות."),
    Indicator("known-webshell-marker", _rx(r"(c99shell|r57shell|\bwso\b\s*2\.|b374k|filesman|indoxploit|china\s*chopper)"), "High",
              "מחרוזת המזוהה עם webshell ציבורי ידוע (שם/גרסה) -- בדקו את הקובץ המלא מיידית."),
    LONG_BASE64_BLOB,
]

PYTHON_INDICATORS: list[Indicator] = [
    Indicator("eval-exec-compile", _rx(r"\b(eval|exec|compile)\s*\("), "High",
              "eval()/exec()/compile() מריצים מחרוזת כקוד Python."),
    Indicator("encode-decode-chain", _rx(r"(base64\.b64decode|binascii\.unhexlify|zlib\.decompress|codecs\.decode)\s*\("), "Medium",
              "שרשרת פענוח נפוצה להסתרת payload -- בדקו אם התוצאה מוזנת ל-eval/exec."),
    Indicator("os-system", _rx(r"\bos\.system\s*\("), "High",
              "os.system() מריץ פקודת shell."),
    Indicator("subprocess-shell-true", _rx(r"subprocess\.(Popen|call|run|check_output)\s*\([^)]*shell\s*=\s*True"), "High",
              "subprocess עם shell=True -- ריצת פקודה דרך shell, סיכון הזרקה אם הארגומנט לא קבוע."),
    Indicator("os-popen", _rx(r"\bos\.popen\s*\("), "Medium",
              "os.popen() מריץ פקודת shell ומחזיר את הפלט."),
    Indicator("dynamic-import-builtins", _rx(r"__import__\s*\(\s*['\"]os['\"]|getattr\s*\(\s*__builtins__"), "High",
              "ייבוא/גישה דינמית ל-builtins -- טכניקת ערפול נפוצה לעקיפת סינון מילות מפתח."),
    Indicator("marshal-pickle-loads", _rx(r"(marshal|pickle)\.loads?\s*\("), "High",
              "פענוח marshal/pickle ממקור לא-מהימן עלול להריץ קוד שרירותי."),
    Indicator("socket-plus-subprocess", _rx(r"\bsocket\.socket\s*\("), "Medium",
              "יצירת socket גולמי -- שילוב עם subprocess/os.system() באותו קובץ הוא דפוס reverse-shell."),
    Indicator("ctypes-shellcode-loader", _rx(r"ctypes\.(CDLL|windll|cdll|memmove|CFUNCTYPE)"), "Medium",
              "שימוש ב-ctypes ברמה נמוכה -- לעיתים משמש לטעינת shellcode; בדקו הקשר."),
    LONG_BASE64_BLOB,
]

JS_TS_INDICATORS: list[Indicator] = [
    Indicator("eval-new-function", _rx(r"\beval\s*\(|new\s+Function\s*\("), "High",
              "eval()/new Function() מריצים מחרוזת כקוד JavaScript."),
    Indicator("timeout-string-exec", _rx(r"set(Timeout|Interval)\s*\(\s*['\"]"), "Medium",
              "setTimeout/setInterval עם מחרוזת (לא פונקציה) מריץ אותה כקוד."),
    Indicator("encode-decode-chain", _rx(r"(Buffer\.from\s*\([^)]*['\"]base64['\"]|atob|unescape|decodeURIComponent)\s*\("), "Medium",
              "שרשרת פענוח (base64/atob/unescape) -- בדקו אם התוצאה מוזנת ל-eval/Function."),
    Indicator("fromcharcode-chain", _rx(r"String\.fromCharCode\s*\((?:\s*\d+\s*,){5,}"), "Medium",
              "String.fromCharCode עם רשימת קודים ארוכה -- טכניקת ערפול נפוצה."),
    Indicator("child-process-exec", _rx(r"require\s*\(\s*['\"]child_process['\"]\s*\)|from\s+['\"]child_process['\"]"), "High",
              "ייבוא child_process -- מאפשר הרצת פקודות מערכת הפעלה מ-Node.js."),
    Indicator("exec-execsync-spawn", _rx(r"\.(exec|execSync|spawn|spawnSync)\s*\("), "Medium",
              "קריאה להרצת פקודה חיצונית (child_process API) -- בדקו מקור הארגומנטים."),
    Indicator("dangerous-innerhtml-write", _rx(r"\.innerHTML\s*=|document\.write\s*\("), "Low",
              "כתיבה ישירה ל-DOM -- בדיקה אם המקור הוא נתון מפוענח/לא-מהימן (XSS/loader בצד-לקוח)."),
    Indicator("beacon-exfil", _rx(r"navigator\.sendBeacon\s*\(|new\s+Image\s*\(\s*\)\.src\s*="), "Low",
              "ערוצי הדלפת-מידע שקטים נפוצים בצד-לקוח (beacon/pixel) -- בדקו את היעד."),
    Indicator("suspicious-url-literal", _rx(r"https?://\d{1,3}(?:\.\d{1,3}){3}"), "Low",
              "כתובת URL עם IP גולמי (לא דומיין) -- נפוץ ב-stagers/C2, פחות נפוץ בקוד לגיטימי."),
    LONG_BASE64_BLOB,
]

LANGUAGE_INDICATORS = {
    "php": PHP_INDICATORS,
    "python": PYTHON_INDICATORS,
    "javascript": JS_TS_INDICATORS,
}

# package.json install-hook scripts are the single most common npm
# supply-chain-attack vector (preinstall/postinstall running arbitrary
# shell) -- checked as a special case, not a per-line regex.
NPM_HOOK_KEYS = ("preinstall", "install", "postinstall", "prepare")
NPM_HOOK_SUSPECT = _rx(r"curl |wget |base64|node -e|eval\(|http://|https://")


@dataclass
class Finding:
    file: str
    line: int
    category: str
    severity: str
    description: str
    snippet: str


def detect_language(path: Path) -> str | None:
    return EXTENSION_LANGUAGE.get(path.suffix.lower())


def scan_package_json(path: Path) -> list[Finding]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return []
    scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
    findings = []
    for key in NPM_HOOK_KEYS:
        value = scripts.get(key)
        if value and NPM_HOOK_SUSPECT.search(value):
            findings.append(Finding(
                file=str(path), line=0, category="npm-install-hook",
                severity="High",
                description=f'סקריפט "{key}" ב-package.json רץ אוטומטית ב-npm install '
                             "ומכיל תבנית חשודה (הורדה/קידוד/eval) -- וקטור נפוץ להתקפות שרשרת אספקה.",
                snippet=f'"{key}": "{value}"',
            ))
    return findings


def scan_file(path: Path, lang_override: str | None = None) -> list[Finding]:
    if path.name == "package.json":
        return scan_package_json(path)

    lang = lang_override or detect_language(path)
    if lang is None or lang not in LANGUAGE_INDICATORS:
        return []

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    findings: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for indicator in LANGUAGE_INDICATORS[lang]:
            if indicator.pattern.search(line):
                snippet = line.strip()
                if len(snippet) > 160:
                    snippet = snippet[:157] + "..."
                findings.append(Finding(
                    file=str(path), line=line_no, category=indicator.name,
                    severity=indicator.severity, description=indicator.description,
                    snippet=snippet,
                ))
    return findings


def iter_files(root: Path, skip_dirs: set[str]) -> list[Path]:
    if root.is_file():
        return [root]
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix.lower() in EXTENSION_LANGUAGE or path.name == "package.json":
            files.append(path)
    return files


SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def print_findings(findings: list[Finding]) -> None:
    if not findings:
        print("לא נמצאו התאמות לאף אינדיקטור -- זה *לא* אישור שהקובץ נקי, "
              "רק שאף דפוס מהרשימה המובנית לא נצפה.")
        return
    findings_sorted = sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.file, f.line))
    for f in findings_sorted:
        loc = f"{f.file}:{f.line}" if f.line else f.file
        print(f"[{f.severity:6}] {loc} -- {f.category}")
        print(f"          {f.description}")
        if f.snippet:
            print(f"          > {f.snippet}")
        print()
    counts = {}
    for f in findings_sorted:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    summary = ", ".join(f"{sev}: {counts[sev]}" for sev in ("High", "Medium", "Low") if sev in counts)
    print(f"סה\"כ {len(findings_sorted)} התאמות ({summary}). כל התאמה היא עוגן לבדיקה ידנית -- לא מסקנה.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="כלי סיוע לאנליטיקה ידנית (סטטית, לא-מבצעת) של קוד PHP/Python/"
                     "JavaScript-TypeScript חשוד -- לעולם לא מריץ/מייבא/מעריך את הקובץ הנסרק, "
                     "רק מחפש תבניות טקסטואליות ידועות כעוגני חקירה.",
    )
    parser.add_argument("path", help="קובץ בודד או תיקייה לסריקה רקורסיבית")
    parser.add_argument("--lang", choices=["auto", "php", "python", "javascript"], default="auto",
                         help="כפיית שפה במקום זיהוי לפי סיומת קובץ (ברירת מחדל: auto)")
    parser.add_argument("--include-vendor", action="store_true",
                         help=f"אל תדלג על תיקיות תלויות/VCS ({', '.join(sorted(DEFAULT_SKIP_DIRS))})")
    parser.add_argument("--min-severity", choices=["High", "Medium", "Low"], default="Low",
                         help="הצג רק ממצאים ברמת חומרה זו ומעלה (ברירת מחדל: Low, כלומר הכול)")
    parser.add_argument("--json", action="store_true", help="פלט JSON במקום טקסט קריא")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.path)
    if not root.exists():
        print(f"שגיאה: הנתיב {root} לא קיים.", file=sys.stderr)
        return 1

    lang_override = None if args.lang == "auto" else args.lang
    skip_dirs = set() if args.include_vendor else DEFAULT_SKIP_DIRS

    all_findings: list[Finding] = []
    for file_path in iter_files(root, skip_dirs):
        all_findings.extend(scan_file(file_path, lang_override))

    min_rank = SEVERITY_ORDER[args.min_severity]
    all_findings = [f for f in all_findings if SEVERITY_ORDER.get(f.severity, 9) <= min_rank]

    if args.json:
        print(json.dumps([f.__dict__ for f in all_findings], ensure_ascii=False, indent=2))
    else:
        print_findings(all_findings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
