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

## אנליטיקה ידנית של קוד PHP/Python/JS-TS חשוד — כלים קיימים ומוכרים

בשונה משאר הכלים בתיקייה זו, לצורך הסקירה הידנית של קובץ חשוד (למשל
webshell שהתגלה בעקבות ממצא CWE-434, פרק 10) **אין צורך בכלי חדש** —
זהו תחום שבו קיימים כלי קוד-פתוח בוגרים, נבדקים היטב, ומתוחזקים באופן
פעיל. הטבלה הבאה ממפה כל שפה לכלי המקובל בתעשייה, עם פקודת התקנה
והרצה מינימלית. כולם **סטטיים** (לא מריצים את הקובץ הנסרק) וניתנים
להרצה אופליין לאחר ההתקנה החד-פעמית (חלקם דורשים הורדת חוקים/רשימות
חתימה מעודכנות מדי פעם מהאינטרנט):

| שפה/היקף | כלי | התקנה | הרצה בסיסית |
|---|---|---|---|
| רב-לשוני (PHP/Python/JS/TS ועוד) | **Semgrep** — מנוע כללי-בדיקה סטטיים עם ruleset ציבורי עצום | `pip install semgrep` | `semgrep --config p/security-audit --config p/secrets ./path` |
| PHP (webshells/malware במיוחד) | **PHP-Malware-Finder** — חוקי YARA ייעודיים לזיהוי webshells וקוד PHP מעורפל | `git clone https://github.com/nbs-system/php-malware-finder` + `pip install yara-python` | `yara -r php-malware-finder/php.yar suspect.php` |
| Python (SAST) | **Bandit** — סורק אבטחה סטטי רשמי של PyCQA | `pip install bandit` | `bandit -r ./path` |
| JavaScript/TypeScript | **ESLint** + `eslint-plugin-security` / `eslint-plugin-no-unsanitized` | `npm install --save-dev eslint eslint-plugin-security` | `npx eslint --plugin security --rule '{"security/detect-eval-with-expression":"error"}' ./path` |
| npm (שרשרת אספקה) | **`npm audit`** לתלויות ידועות, ועיון ידני ב-`scripts` (`preinstall`/`postinstall`) בקובץ `package.json` | מובנה ב-npm | `npm audit` |
| חתימות כלליות (כל שפה, כל סוג קובץ) | **YARA** עצמו, עם חוקים כלליים (כמו [Neo23x0/signature-base](https://github.com/Neo23x0/signature-base)) | `pip install yara-python` | `yara -r rules.yar suspect_dir/` |

**עיקרון מנחה זהה לשאר הספר**: תוצאת כל אחד מהכלים האלה היא **עוגן
לבדיקה אנושית**, לא פסק דין אוטומטי — Semgrep/Bandit/ESLint-security
מייצרים גם False Positives בקוד לגיטימי (למשל שימוש תקין ב-`eval`
בסקריפט build), ו-YARA תלוי לחלוטין באיכות ובעדכניות קובץ החוקים
שנטען.

לניתוח סטטי עמוק ומבוסס-ML **ל-Python בלבד** (מיצוי תכונות מ-AST, מודל
מאומן, הסבר בשפה טבעית — כלי פנימי של הריפו הזה, לא כלי חיצוני), ראו
את `security_classifier/` בשורש הריפו.

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
