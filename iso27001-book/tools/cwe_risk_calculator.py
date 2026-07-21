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
#                            impact_availability, test_protocol), each
#                            impact 1-5. test_protocol is a concise
#                            description (Hebrew) of the pentest technique
#                            used to actually verify that weakness in an
#                            authorized engagement -- see book chapter 9,
#                            section 9.14 ("per-CWE" testing protocols).
# These are illustrative defaults, not measured facts about any system.
# ---------------------------------------------------------------------------
CWE_BASELINE: dict[str, dict] = {
    "CWE-79": {"name": "Cross-Site Scripting (XSS)", "category": "Web / קלט משתמש",
               "likelihood": 4, "impact_c": 3, "impact_i": 3, "impact_a": 1,
               "test_protocol": "הזרקת payloads (<script>, event handlers, payloads מקודדים) לכל "
                                 "פרמטר קלט המוצג בדף; אימות הרצה בפועל בהקשר ה-DOM/attribute/JS "
                                 "(reflected/stored/DOM-based)."},
    "CWE-89": {"name": "SQL Injection", "category": "Web / קלט משתמש",
               "likelihood": 4, "impact_c": 5, "impact_i": 5, "impact_a": 4,
               "test_protocol": "הזרקת payloads בוליאניים/מבוססי-זמן/מבוססי-שגיאה (' OR '1'='1, "
                                 "SLEEP(5)) בכל פרמטר; ניתוח הבדלי תגובה; אימות עם חילוץ מבוקר "
                                 "(UNION-based) תחת ROE בלבד."},
    "CWE-78": {"name": "OS Command Injection", "category": "Web / קלט משתמש",
               "likelihood": 3, "impact_c": 5, "impact_i": 5, "impact_a": 5,
               "test_protocol": "הזרקת מפרידי פקודות (; | && `$()`) לפרמטרים שעשויים לעבור ל-shell; "
                                 "זיהוי עיכוב מכוון (sleep) כאינדיקציה עיוורת; אימות בסביבת בדיקה מבוקרת."},
    "CWE-94": {"name": "Code Injection", "category": "Web / קלט משתמש",
               "likelihood": 3, "impact_c": 5, "impact_i": 5, "impact_a": 5,
               "test_protocol": "הזרקת payloads לשפת תבנית/eval (SSTI, למשל {{7*7}}); זיהוי חישוב "
                                 "בפועל בתגובה כאינדיקציה לביצוע קוד."},
    "CWE-22": {"name": "Path Traversal", "category": "Web / קלט משתמש",
               "likelihood": 4, "impact_c": 4, "impact_i": 3, "impact_a": 2,
               "test_protocol": "בקשת נתיבים עם ../ (מקודד/לא-מקודד) לקבצים ידועים (/etc/passwd, "
                                 "web.config); בדיקת עקיפת סינון עם null-byte/double-encoding."},
    "CWE-352": {"name": "Cross-Site Request Forgery (CSRF)", "category": "Web / הרשאות",
                "likelihood": 3, "impact_c": 2, "impact_i": 4, "impact_a": 1,
                "test_protocol": "בניית טופס/בקשה חוצה-מקור ללא טוקן CSRF תקף; אימות שהפעולה "
                                  "מתבצעת בהצלחה כשמשתמש מחובר פותח עמוד חיצוני זדוני."},
    "CWE-434": {"name": "Unrestricted Upload of Dangerous File Type", "category": "Web / קלט משתמש",
                "likelihood": 3, "impact_c": 4, "impact_i": 5, "impact_a": 4,
                "test_protocol": "העלאת קבצים עם סיומות מבוצעות (.php/.jsp/.aspx) תוך מניפולציית "
                                  "Content-Type/magic bytes/double extension; אימות שהקובץ נגיש "
                                  "ומופעל בשרת."},
    "CWE-502": {"name": "Deserialization of Untrusted Data", "category": "Web / קלט משתמש",
                "likelihood": 2, "impact_c": 5, "impact_i": 5, "impact_a": 4,
                "test_protocol": "איתור נקודות קצה שמקבלות אובייקטים מסודרים (Java/PHP/Python "
                                  "pickle וכו') והזרקת gadget chains ידועים (ysoserial וכד') "
                                  "במסגרת ROE בלבד."},
    "CWE-611": {"name": "Improper Restriction of XML External Entity Reference (XXE)",
                "category": "Web / קלט משתמש",
                "likelihood": 2, "impact_c": 5, "impact_i": 3, "impact_a": 3,
                "test_protocol": "שליחת מסמכי XML עם DOCTYPE/ENTITY חיצוני המצביע לקובץ מקומי או "
                                  "URL פנימי; בדיקת אקספילטרציה מחוץ-לפס (OOB, למשל דרך DNS/HTTP "
                                  "callback)."},
    "CWE-287": {"name": "Improper Authentication", "category": "זהות והרשאות",
                "likelihood": 4, "impact_c": 4, "impact_i": 4, "impact_a": 2,
                "test_protocol": "בדיקת עקיפה/החלשה של זרימת האימות: ניחוש/brute-force מבוקר לפי "
                                  "ROE, בדיקת עקיפת 2FA, session fixation, ובדיקת נתיבי אימות "
                                  "חלופיים (למשל API ישן)."},
    "CWE-306": {"name": "Missing Authentication for Critical Function", "category": "זהות והרשאות",
                "likelihood": 3, "impact_c": 5, "impact_i": 5, "impact_a": 4,
                "test_protocol": "גישה ישירה ל-endpoint רגיש (API ניהולי, פעולת עדכון) ללא כל "
                                  "טוקן/session; השוואה מול קריאה מאומתת לאותה פעולה."},
    "CWE-862": {"name": "Missing Authorization", "category": "זהות והרשאות",
                "likelihood": 4, "impact_c": 4, "impact_i": 4, "impact_a": 2,
                "test_protocol": "גישה ל-endpoint עם session ברמת הרשאה נמוכה (או ללא session "
                                  "כלל) ובדיקה אם מידע/פעולה מוגבלים מוחזרים בכל זאת — ראו דוגמת "
                                  "milatova ב-9.6."},
    "CWE-863": {"name": "Incorrect Authorization", "category": "זהות והרשאות",
                "likelihood": 3, "impact_c": 4, "impact_i": 4, "impact_a": 2,
                "test_protocol": "שינוי מזהי אובייקט (IDOR) בבקשות בין שני משתמשי-בדיקה שונים; "
                                  "בדיקה אם ניתן לגשת/לשנות נתוני המשתמש האחר."},
    "CWE-269": {"name": "Improper Privilege Management", "category": "זהות והרשאות",
                "likelihood": 3, "impact_c": 4, "impact_i": 5, "impact_a": 3,
                "test_protocol": "ניסיון הסלמת הרשאות אופקית/אנכית — שינוי role/claim בטוקן JWT או "
                                  "בפרמטר בקשה, ובדיקה אם השרת מכבד ערך שנשלח מהלקוח."},
    "CWE-798": {"name": "Use of Hard-coded Credentials", "category": "ניהול סודות",
                "likelihood": 3, "impact_c": 5, "impact_i": 4, "impact_a": 2,
                "test_protocol": "חיפוש מחרוזות/מפתחות בקוד המקור, בהיסטוריית git, בקבצי תצורה "
                                  "שנחשפו (.env, config.json), ובבינארי/אפליקציית מובייל שפורקו."},
    "CWE-321": {"name": "Use of Hard-coded Cryptographic Key", "category": "ניהול סודות",
                "likelihood": 2, "impact_c": 5, "impact_i": 4, "impact_a": 1,
                "test_protocol": "חילוץ מפתחות קבועים מקוד/בינארי/אפליקציית מובייל; אימות אם הם "
                                  "משמשים בפועל להצפנה/חתימה בסביבת הפרודקשן."},
    "CWE-522": {"name": "Insufficiently Protected Credentials", "category": "ניהול סודות",
                "likelihood": 3, "impact_c": 5, "impact_i": 3, "impact_a": 1,
                "test_protocol": "בדיקת שידור/אחסון סיסמאות בטקסט גלוי (פרמטרי URL, עוגיות לא "
                                  "מוצפנות, לוגים); אימות מדיניות ה-hashing (bcrypt/argon2 מול "
                                  "MD5/SHA1 גולמי)."},
    "CWE-259": {"name": "Use of Hard-coded Password", "category": "ניהול סודות",
                "likelihood": 3, "impact_c": 5, "impact_i": 4, "impact_a": 2,
                "test_protocol": "כמו CWE-798 אך ממוקד בסיסמה ספציפית — חיפוש בקוד/תצורה, וניסיון "
                                  "שימוש מול ממשקי ניהול/בסיסי נתונים שהתגלו."},
    "CWE-200": {"name": "Exposure of Sensitive Information to an Unauthorized Actor",
                "category": "חשיפת מידע",
                "likelihood": 4, "impact_c": 4, "impact_i": 1, "impact_a": 1,
                "test_protocol": "השוואת תגובות מאומתות מול לא-מאומתות לאותו endpoint; חיפוש "
                                  "שדות edit-context/פנימיים שדולפים בתגובה ציבורית (ראו דוגמת "
                                  "wp/v2/users ב-9.6)."},
    "CWE-209": {"name": "Generation of Error Message Containing Sensitive Information",
                "category": "חשיפת מידע",
                "likelihood": 4, "impact_c": 2, "impact_i": 1, "impact_a": 1,
                "test_protocol": "טריגור מכוון לשגיאות (קלט לא תקין, טיפוסים שגויים) ובדיקה אם "
                                  "stack trace/נתיבי קבצים/גרסאות נחשפים בתגובה."},
    "CWE-732": {"name": "Incorrect Permission Assignment for Critical Resource",
                "category": "תצורה",
                "likelihood": 3, "impact_c": 4, "impact_i": 4, "impact_a": 3,
                "test_protocol": "בדיקת הרשאות קבצים/משאבים (world-writable, ACL רופפים, דליים "
                                  "ציבוריים בענן כמו S3) בסביבות שיש אליהן גישה."},
    "CWE-284": {"name": "Improper Access Control", "category": "זהות והרשאות",
                "likelihood": 4, "impact_c": 4, "impact_i": 4, "impact_a": 3,
                "test_protocol": "מיפוי שיטתי של כל ה-endpoints/פעולות מול מטריצת הרשאות מוגדרת "
                                  "מראש, ובדיקת כל שילוב role×פעולה לאיתור חריגות."},
    "CWE-190": {"name": "Integer Overflow or Wraparound", "category": "לוגיקה / זיכרון",
                "likelihood": 2, "impact_c": 2, "impact_i": 3, "impact_a": 3,
                "test_protocol": "הזנת ערכים בקצוות טווח (MAX_INT, ערכים שליליים) בשדות מספריים; "
                                  "בדיקת עקיפת בדיקות תקציב/מכסה או הקצאת זיכרון שגויה."},
    "CWE-125": {"name": "Out-of-bounds Read", "category": "לוגיקה / זיכרון",
                "likelihood": 3, "impact_c": 4, "impact_i": 1, "impact_a": 3,
                "test_protocol": "פאזינג (fuzzing) קלטים בינאריים/פרוטוקולים מותאמים עם ערכי "
                                  "אורך/אינדקס חריגים; ניטור קריסות/דליפת זיכרון ברכיבי native."},
    "CWE-787": {"name": "Out-of-bounds Write", "category": "לוגיקה / זיכרון",
                "likelihood": 3, "impact_c": 4, "impact_i": 5, "impact_a": 4,
                "test_protocol": "פאזינג דומה ל-CWE-125 עם מעקב קריסות המעידות על שכתוב זיכרון, "
                                  "לרוב עם sanitizers (ASAN) בסביבת בדיקה מבוקרת."},
    "CWE-416": {"name": "Use After Free", "category": "לוגיקה / זיכרון",
                "likelihood": 2, "impact_c": 4, "impact_i": 4, "impact_a": 4,
                "test_protocol": "בדיקה דינמית עם sanitizers (ASAN) בסביבת פיתוח/בדיקה ברכיבי "
                                  "native — לא מומלץ/אפשרי לבדוק ישירות מול פרודקשן."},
    "CWE-476": {"name": "NULL Pointer Dereference", "category": "לוגיקה / זיכרון",
                "likelihood": 3, "impact_c": 1, "impact_i": 1, "impact_a": 4,
                "test_protocol": "שליחת קלטים חסרים/ריקים (missing fields, null JSON) לנקודות "
                                  "קצה; בדיקת קריסה/DoS כתוצאה מכך."},
    "CWE-311": {"name": "Missing Encryption of Sensitive Data", "category": "הצפנה",
                "likelihood": 3, "impact_c": 5, "impact_i": 2, "impact_a": 1,
                "test_protocol": "בדיקת ערוצי העברה (HTTP מול HTTPS) ואחסון (גיבויים, buckets) "
                                  "ללא הצפנה at-rest; ניתוח תעבורה (mitmproxy/Wireshark)."},
    "CWE-327": {"name": "Use of a Broken or Risky Cryptographic Algorithm", "category": "הצפנה",
                "likelihood": 2, "impact_c": 4, "impact_i": 3, "impact_a": 1,
                "test_protocol": "זיהוי אלגוריתמים חלשים (MD5/SHA1/DES/RC4) ב-TLS handshake, "
                                  "בקוד, או באחסון סיסמאות; שימוש בכלים כמו testssl.sh/sslyze."},
    "CWE-330": {"name": "Use of Insufficiently Random Values", "category": "הצפנה",
                "likelihood": 2, "impact_c": 3, "impact_i": 3, "impact_a": 1,
                "test_protocol": "דגימת מספר טוקנים/מזהי-session/reset-password ברצף ובדיקת "
                                  "דפוס/entropy נמוך; ניסיון חיזוי או שכפול טוקן."},
    "CWE-918": {"name": "Server-Side Request Forgery (SSRF)", "category": "Web / רשת",
                "likelihood": 3, "impact_c": 4, "impact_i": 3, "impact_a": 3,
                "test_protocol": "הזנת URL פנימי/כתובת מטא-דאטה של ענן (169.254.169.254) בפרמטר "
                                  "שמבצע בקשת HTTP מהשרת; אימות SSRF עיוור עם callback חוץ-לפס."},
    "CWE-400": {"name": "Uncontrolled Resource Consumption", "category": "זמינות",
                "likelihood": 3, "impact_c": 1, "impact_i": 1, "impact_a": 5,
                "test_protocol": "שליחת בקשות/קלטים כבדים (payload גדול, regex עם ReDoS, בקשות "
                                  "מרובות) בסביבת בדיקה מבוקרת בלבד ובאישור ROE מפורש — לרוב אסור "
                                  "בפרודקשן (ראו 9.7)."},
    "CWE-668": {"name": "Exposure of Resource to Wrong Sphere", "category": "תצורה",
                "likelihood": 3, "impact_c": 3, "impact_i": 3, "impact_a": 2,
                "test_protocol": "בדיקת גישה חוצה-דיירים (multi-tenant) — ניסיון גישה למשאבי דייר "
                                  "אחר עם session תקף של הדייר הנוכחי."},
    "CWE-1188": {"name": "Insecure Default Initialization of Resource", "category": "תצורה",
                 "likelihood": 3, "impact_c": 3, "impact_i": 3, "impact_a": 2,
                 "test_protocol": "סקירת תצורת ברירת מחדל של רכיבים שהותקנו (DB, שירותי ענן, "
                                   "קונטיינרים) לאיתור admin/admin, פאנלים פתוחים, הרשאות ציבוריות "
                                   "שלא שונו לאחר ההתקנה."},
    "CWE-20": {"name": "Improper Input Validation", "category": "קלט משתמש",
               "likelihood": 4, "impact_c": 3, "impact_i": 3, "impact_a": 2,
               "test_protocol": "פאזינג שיטתי של כל שדות הקלט עם ערכים חריגים/סוג שגוי/תווים "
                                 "מיוחדים, כבסיס לאיתור חולשות ממוקדות יותר (הזרקה, עקיפת ולידציה "
                                 "עסקית)."},
    # Frequently seen in web/network pentest reports (see chapter 9):
    "CWE-16": {"name": "Configuration (general security misconfiguration)", "category": "תצורה",
               "likelihood": 4, "impact_c": 3, "impact_i": 2, "impact_a": 2,
               "test_protocol": "סקירת headers, קבצי חשיפה (robots.txt, .git/, .env), הרשאות "
                                 "ברירת מחדל ושירותים חשופים מיותרים — בדרך כלל שלב recon ראשוני "
                                 "(ראו tools/fingerprint.py ב-pentest-booknet)."},
    "CWE-295": {"name": "Improper Certificate Validation", "category": "רשת / TLS",
                "likelihood": 2, "impact_c": 4, "impact_i": 3, "impact_a": 1,
                "test_protocol": "בדיקה שהלקוח (אפליקציה/שירות-לשירות) מקבל תעודות לא-תקינות/"
                                  "self-signed/פגות-תוקף ללא שגיאה, בעזרת MITM proxy מבוקר."},
    "CWE-319": {"name": "Cleartext Transmission of Sensitive Information", "category": "רשת / TLS",
                "likelihood": 3, "impact_c": 4, "impact_i": 2, "impact_a": 1,
                "test_protocol": "ניתוח תעבורת רשת (mitmproxy/Wireshark) לאיתור HTTP לא-מוצפן, "
                                  "פרוטוקולים legacy (FTP/Telnet), או נפילה לגרסת TLS ישנה."},
    "CWE-346": {"name": "Origin Validation Error", "category": "Web / רשת",
                "likelihood": 2, "impact_c": 3, "impact_i": 3, "impact_a": 1,
                "test_protocol": "בדיקת הגדרות CORS (Access-Control-Allow-Origin: * עם "
                                  "credentials, reflect של כותרת Origin) וניסיון קריאה חוצה-מקור "
                                  "עם עוגיות/טוקן."},
    "CWE-601": {"name": "URL Redirection to Untrusted Site (Open Redirect)", "category": "Web / קלט משתמש",
                "likelihood": 3, "impact_c": 2, "impact_i": 2, "impact_a": 1,
                "test_protocol": "הזנת URL חיצוני בפרמטרי redirect (?next=, ?return_url=) ואימות "
                                  "הפניה בפועל לאתר חיצוני — שימושי כשלב תמיכה בפישינג."},
    "CWE-1021": {"name": "Improper Restriction of Rendered UI Layers (Clickjacking)", "category": "Web / תצורה",
                 "likelihood": 2, "impact_c": 1, "impact_i": 3, "impact_a": 1,
                 "test_protocol": "בדיקת headers (X-Frame-Options, CSP frame-ancestors) והטמעת "
                                   "הדף ב-iframe בעמוד בדיקה כדי לוודא חסימה בפועל."},
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
            "test_protocol": baseline["test_protocol"],
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


def cmd_protocol(args: argparse.Namespace) -> None:
    """Print the pentest testing protocol(s) for one or all baseline CWEs (book ch. 9, 9.14)."""
    if args.cwe:
        cwe_id = args.cwe.upper()
        data = CWE_BASELINE.get(cwe_id)
        if data is None:
            print(f"שגיאה: {cwe_id} אינו ברשימת ה-CWE הבסיסית של הכלי.", file=sys.stderr)
            sys.exit(1)
        print(f"{cwe_id} — {data['name']}\n")
        print(data["test_protocol"])
        return
    for cwe_id, data in sorted(CWE_BASELINE.items()):
        print(f"{cwe_id} — {data['name']}")
        print(f"  {data['test_protocol']}\n")


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

    p_protocol = sub.add_parser(
        "protocol",
        help="הצג את פרוטוקול בדיקת החדירה (test protocol) עבור CWE בודד, או עבור כל הרשימה",
    )
    p_protocol.add_argument("--cwe", help="מזהה CWE ספציפי, למשל CWE-89 (השמט כדי להציג את כל הרשימה)")
    p_protocol.set_defaults(func=cmd_protocol)

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
