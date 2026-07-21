# כלים נלווים לספר

## `cwe_risk_calculator.py` — מחשבון סקר סיכונים לפי CWE

כלי שורת-פקודה **המפעיל אופליין לחלוטין** (ללא רשת, ללא תלות בחבילות
חיצוניות) המיישם מודל ניקוד סיכונים **Likelihood × Impact** (מטריצת 5×5),
בהתאם למתודולוגיה המתוארת ב-ISO/IEC 27005 ומיושמת בסעיף 6.1.2 של
ISO/IEC 27001 (ראו [פרק 2](../02-mivne-tekhen-27001.md) ו-[פרק 6](../06-yisum-maasi.md)).

הכלי כולל טבלת בסיס קטנה ומתוחזקת-ידנית של חולשות **CWE** נפוצות (מבוססת
בעיקרה על חולשות שחוזרות ברשימות "CWE Top 25 Most Dangerous Software
Weaknesses"), עם הצעות ברירת-מחדל לסבירות ולהשפעה על סודיות/שלמות/זמינות
לכל CWE. אלו **ערכי פתיחה להמחשה בלבד** — כל ארגון חייב לכייל אותם למציאות
שלו (סוג הנכס, חשיפה, בקרות מפצות קיימות וכו') לפני שהם משמשים בפועל
בהצהרת ההתאמה (SoA) או ברשומת הסיכונים הרשמית.

### שימוש

```bash
# הצגת טבלת ה-CWE הבסיסית הכלולה בכלי
python3 cwe_risk_calculator.py list

# ניקוד CWE בודד, עם דריסת ברירת המחדל של הסבירות
python3 cwe_risk_calculator.py score --cwe CWE-89 --asset "פורטל לקוחות" --likelihood 3

# ניקוד קובץ ממצאים שלם (JSON או CSV) והפקת רשומת סיכונים ממוינת
python3 cwe_risk_calculator.py report --input sample_findings.json --output risk_register.csv

# פרוטוקול בדיקת חדירה (test protocol) עבור CWE ספציפי, או עבור כל 41 ה-CWE-ים
python3 cwe_risk_calculator.py protocol --cwe CWE-862
python3 cwe_risk_calculator.py protocol
```

כל רשומת CWE בטבלת הבסיס כוללת גם שדה `test_protocol` — תיאור קונקרטי של
טכניקת הבדיקה שבודק חדירה מורשה מפעיל כדי לאמת את קיום החולשה בפועל (לא
רק ניקוד חומרה תיאורטי). השדה הזה מופיע גם בפלט `score`/`report`, כך
שממצא מנוקד ופרוטוקול האימות שלו יוצאים מאותה הרצה. ראו פרק 9, סעיף 9.14
בספר לטבלה המלאה (זהה לזו שבקוד) ולהסבר על הרעיון.

מבנה קובץ ממצאים (JSON או CSV) לפקודת `report`: שדה חובה `cwe_id`, ושדות
אופציונליים `asset`, `likelihood`, `impact_c`, `impact_i`, `impact_a`,
`notes` — כל שדה שלא סופק נלקח מטבלת ברירת המחדל של הכלי. דוגמה כללית ב-
`sample_findings.json`, ודוגמה מבוססת על שני ממצאי pentest **אמיתיים**
מתוך `pentest-milatova/` (בשורש הריפו) ב-`pentest_case_study_findings.json`
— ראו פירוט מלא בפרק 9 של הספר (9.6), כולל הסבר מדוע ממצא אחד דורש דריסה
ידנית של ברירת המחדל כדי לשקף נכון את ההקשר.

### מודל הניקוד

`score = likelihood (1–5) × max(impact_c, impact_i, impact_a) (1–5)`

| טווח ציון | רמת סיכון |
|-----------|-----------|
| 1–4       | נמוך (Low) |
| 5–9       | בינוני (Medium) |
| 10–16     | גבוה (High) |
| 17–25     | קריטי (Critical) |

מודל זה הוא דוגמה פדגוגית פשוטה ונפוצה, לא דרישה נורמטיבית של התקן —
ISO/IEC 27005 משאיר את בחירת המתודולוגיה המדויקת לארגון, ובלבד שהיא עקבית
וניתנת לשחזור (ראו סעיף 6.1.2 בפרק 2).

## `malicious_code_triage.py` — אנליטיקה ידנית של קוד PHP/Python/JS-TS חשוד

כלי CLI **סטטי בלבד** — לעולם לא מריץ, מייבא, או מעריך (`eval`) את הקובץ
הנסרק, ומעולם לא מתחבר לרשת. הוא מיועד לשלב שבו כבר יש בידכם קובץ חשוד
(למשל webshell שהתגלה בעקבות ממצא CWE-434, פרק 10) וצריך **לעבור עליו
ידנית** ביעילות — הכלי מסמן שורות שתואמות תבניות ידועות (הרצת קוד
דינמית, שרשראות קידוד/פענוח, הרצת פקודות מערכת, superglobals/קלט
זורם ישירות לפונקציית הרצה, מחרוזות base64 ארוכות, מזהים של webshells
ציבוריים ידועים, ו-hooks חשודים ב-`package.json` שרצים אוטומטית
ב-`npm install`) — **תמיד כעוגן לבדיקה אנושית, לא כפסק דין אוטומטי**:
לכל דפוס יש שימושים לגיטימיים, וההקשר קובע.

לניתוח סטטי עמוק ומבוסס-ML **ל-Python בלבד** (מיצוי תכונות מ-AST, מודל
מאומן, הסבר בשפה טבעית), ראו את `security_classifier/` בשורש הריפו —
כלי זה הוא "האח הקל" שלו: פחות מדויק אך תומך בשלוש שפות ומתמקד בזרימת
עבודה ידנית ומהירה במקום ניקוד אוטומטי.

### שימוש

```bash
# סריקת קובץ בודד (זיהוי שפה אוטומטי לפי סיומת)
python3 malicious_code_triage.py suspect.php

# סריקת תיקייה שלמה רקורסיבית (מדלג כברירת מחדל על node_modules/vendor/.git)
python3 malicious_code_triage.py ./uploaded_files/

# הצגת High בלבד, ופלט JSON למיזוג עם כלים אחרים
python3 malicious_code_triage.py ./uploaded_files/ --min-severity High --json
```

### קטגוריות אינדיקטורים לדוגמה

| שפה | דוגמאות אינדיקטורים |
|---|---|
| PHP | `eval()`/`assert()`/`create_function()`, שרשראות `base64_decode`/`gzinflate`, `system()`/`exec()`/backticks, `$_GET`/`$_POST` שזורם ישירות לפונקציית הרצה, `$$` (משתני-משתנים), מזהי webshells ציבוריים ידועים |
| Python | `eval`/`exec`/`compile`, `os.system`, `subprocess` עם `shell=True`, `pickle`/`marshal.loads`, ייבוא דינמי של `os` דרך `__import__`/`__builtins__` |
| JavaScript/TypeScript | `eval`/`new Function`, `child_process` (`exec`/`execSync`/`spawn`), שרשראות `atob`/`Buffer.from(...,'base64')`, `String.fromCharCode` ארוך, `package.json` עם `postinstall`/`preinstall` חשוד |

## `build_book_pdf.py` — הפקת הספר כקובץ PDF יחיד

מרכיב את כל פרקי הספר (`README.md` + `01`–`11` + `tools/README.md` כנספח)
לקובץ PDF אחד עם עימוד RTL תקין, תוכן עניינים מקושר (קישורים פנימיים
בין הפרקים הופכים לעוגנים בתוך אותו PDF), טבלאות, ובלוקי קוד ב-LTR.
דורש שתי תלויות אופציונליות שאינן חלק מהליבה של שאר הריפו:

```bash
pip install weasyprint markdown

python3 iso27001-book/tools/build_book_pdf.py
# כותב ל: iso27001-book/ISO-27001-Summary-Book-HE.pdf
```

הריצו מחדש בכל פעם שמעדכנים פרק, כדי שה-PDF המצורף יישאר מסונכרן עם
קבצי ה-Markdown (מקור האמת של הספר).
