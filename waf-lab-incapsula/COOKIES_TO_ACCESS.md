# שימוש ב-Cookies כדי להכנס פנימה

## מהם ה-Cookies האלה?

כשהריצו את `stealth_browser_bypass.py`, הקבלתם cookies מ-Incapsula:

```
visid_incap_2160523: ej+FBookSkqj0TSIWYL0QY/yYWoAAAAAQUIPAAAAAABTBFYjUY
incap_ses_3302_2160523: 89t5NrUhOU8s4VBsqw/TLY/yYWoAAAAAXYwU7BvLOD9vQ1QSFb
```

**מה הם:**
- `visid_incap_*` - זיהוי ייחודי למבקר (Visitor ID)
- `incap_ses_*` - סשן שעבר את אתגר Incapsula (Session)

**למה הם עובדים:**
- הם נוצרו על ידי דפדפן אמיתי
- הם עברו את כל בדיקות הזיהוי של Incapsula
- ה-Incapsula תיקבל אותם בתור בקשה חוקית

---

## איך להשתמש בהם?

### דרך 1: Command Line (הפשוטה ביותר)

```bash
python3 tools/authenticated_requests.py \
  https://target.com \
  "ej+FBookSkqj0TSIWYL0QY/yYWoAAAAAQUIPAAAAAABTBFYjUY" \
  "89t5NrUhOU8s4VBsqw/TLY/yYWoAAAAAXYwU7BvLOD9vQ1QSFb"
```

**Output:**
```
📨 GET https://target.com/
✓ Status: 200
✓ Size: 45,230 bytes
✓ SUCCESS - Got through!
✓ Content preview: <!DOCTYPE html>...
```

### דרך 2: עם שמירה לקובץ

```bash
# שמור HTML
python3 tools/authenticated_requests.py \
  https://target.com \
  "ej+FBookSkqj0TSIWYL0QY/yYWoAAAAAQUIPAAAAAABTBFYjUY" \
  "89t5NrUhOU8s4VBsqw/TLY/yYWoAAAAAXYwU7BvLOD9vQ1QSFb" \
  --output result.html

# שמור metadata
python3 tools/authenticated_requests.py \
  https://target.com \
  "ej+FBookSkqj0TSIWYL0QY/yYWoAAAAAQUIPAAAAAABTBFYjUY" \
  "89t5NrUhOU8s4VBsqw/TLY/yYWoAAAAAXYwU7BvLOD9vQ1QSFb" \
  --json-output metadata.json
```

### דרך 3: Python Script (עבור קוד)

```python
from authenticated_requests import AuthenticatedRequests

# ייצור session עם cookies
auth = AuthenticatedRequests(
    url='https://target.com',
    visid_cookie='ej+FBookSkqj0TSIWYL0QY/yYWoAAAAAQUIPAAAAAABTBFYjUY',
    incap_ses_cookie='89t5NrUhOU8s4VBsqw/TLY/yYWoAAAAAXYwU7BvLOD9vQ1QSFb'
)

# GET בעמוד הבית
result1 = auth.get('/')
print(f"Status: {result1['status']}")

# GET לנתיב ספציפי
result2 = auth.get('/api/data')

# POST עם דטה
result3 = auth.post('/api/login', data={'user': 'admin', 'pass': '123'})

# Requests רגילים עם headers
result4 = auth.get('/protected', headers={'X-Custom': 'value'})
```

---

## התהליך המלא (Step-by-Step)

### שלב 1: קבלת Cookies עם Browser Bypass

```bash
python3 tools/stealth_browser_bypass.py https://target.com \
  --json-output cookies.json
```

**Output (cookies.json):**
```json
{
  "url": "https://target.com",
  "status": 200,
  "cookies": [
    {
      "name": "visid_incap_2160523",
      "value": "ej+FBookSkqj0TSIWYL0QY/yYWoAAAAAQUIPAAAAAABTBFYjUY"
    },
    {
      "name": "incap_ses_3302_2160523",
      "value": "89t5NrUhOU8s4VBsqw/TLY/yYWoAAAAAXYwU7BvLOD9vQ1QSFb"
    }
  ]
}
```

### שלב 2: שחזור Cookies מ-JSON

```python
import json

with open('cookies.json') as f:
    data = json.load(f)

cookies = {c['name']: c['value'] for c in data['cookies']}
visid = cookies['visid_incap_2160523']
incap_ses = cookies['incap_ses_3302_2160523']

print(f"visid: {visid}")
print(f"incap_ses: {incap_ses}")
```

### שלב 3: כניסה עם Cookies

```bash
python3 tools/authenticated_requests.py \
  https://target.com \
  "$visid" \
  "$incap_ses" \
  --output content.html
```

---

## דוגמאות מעשיות

### דוגמה 1: סקראפ עמוד

```python
from authenticated_requests import AuthenticatedRequests
from bs4 import BeautifulSoup

auth = AuthenticatedRequests(
    url='https://target.com',
    visid_cookie='YOUR_VISID',
    incap_ses_cookie='YOUR_INCAP_SES'
)

# קבל את העמוד
result = auth.get('/')

# Parse HTML
soup = BeautifulSoup(result['content'], 'html.parser')

# חלץ דטה
titles = soup.find_all('h1')
for title in titles:
    print(title.text)
```

### דוגמה 2: API Call

```python
from authenticated_requests import AuthenticatedRequests

auth = AuthenticatedRequests(
    url='https://api.target.com',
    visid_cookie='YOUR_VISID',
    incap_ses_cookie='YOUR_INCAP_SES'
)

# GET API
result = auth.get('/api/users')
print(result['status'])  # 200 = הצלחה!

# POST API
result = auth.post('/api/submit', data={
    'name': 'John',
    'email': 'john@example.com'
})
```

### דוגמה 3: לולאה (מולטיפל Requests)

```python
from authenticated_requests import AuthenticatedRequests

auth = AuthenticatedRequests(
    url='https://target.com',
    visid_cookie='YOUR_VISID',
    incap_ses_cookie='YOUR_INCAP_SES'
)

# Fetch מולטיפל עמודים
pages = ['/', '/about', '/products', '/contact']

for page in pages:
    result = auth.get(page)
    print(f"{page}: {result['status']}")
    
    # שמור לקובץ
    with open(f'page_{page.replace("/", "_")}.html', 'w') as f:
        f.write(result['content'])
```

---

## בדיקה: האם ה-Cookies עובדים?

### Test 1: Basic Request

```bash
python3 tools/authenticated_requests.py \
  https://target.com \
  "YOUR_VISID" \
  "YOUR_INCAP_SES"
```

**אם הצלחה:**
```
✓ Status: 200
✓ SUCCESS - Got through!
```

**אם כשל:**
```
Status: 403
⚠️ Cookies expired or invalid
```

### Test 2: Check Cookie Validity

```python
import requests

# ללא cookies
response = requests.get('https://target.com')
print(f"Without cookies: {response.status_code}")  # 403

# עם cookies
cookies = {
    'visid_incap_2160523': 'ej+FBookSkqj0TSIWYL0QY/yYWoAAAAAQUIPAAAAAABTBFYjUY',
    'incap_ses_3302_2160523': '89t5NrUhOU8s4VBsqw/TLY/yYWoAAAAAXYwU7BvLOD9vQ1QSFb'
}
response = requests.get('https://target.com', cookies=cookies)
print(f"With cookies: {response.status_code}")  # 200
```

---

## טיפול בבעיות

### בעיה: Status 403 (Forbidden)

**סיבות אפשריות:**
1. ה-Cookies פג עליהם (הם תקפים רק לזמן מוגבל)
2. ה-Cookies מה-IP שונה
3. Headers חסרים

**פתרון:**
```bash
# תוך 5 דקות, הפק cookies חדשים
python3 tools/stealth_browser_bypass.py https://target.com --json-output new_cookies.json

# השתמש ב-Cookies החדשים
python3 tools/authenticated_requests.py ...
```

### בעיה: Status 503 + תוכן HTML עם `<iframe id="main-iframe"...>`

**זו לא שגיאת שרת - זה דף הצ'לנג'/CAPTCHA של Incapsula עצמה.** אם ה-preview
מציג משהו שמתחיל ב:

```html
<html style="height:100%"><head><META NAME="ROBOTS" CONTENT="NOINDEX, NOFOLLOW">...
<body style="margin:0px;height:100%"><iframe id=...
```

זו החתימה הידועה של Incapsula שמנפיקה מחדש אתגר/CAPTCHA - כלומר ה-cookies
**נדחו**, למרות שהם תקפים.

**הסיבה השורשית - שני דברים שקשה לזייף:**

1. **קשירת cookies ל-IP.** `visid_incap_*` ו-`incap_ses_*` קשורים לכתובת ה-IP
   שממנה הם הונפקו. אם `stealth_browser_bypass.py` רץ מ-IP אחד (למשל שרת/פרוקסי
   מסוים) ו-`authenticated_requests.py` רץ מ-IP אחר - Incapsula מזהה את
   חוסר-ההתאמה ומחזירה צ'לנג' מחדש במקום התוכן.

2. **טביעת אצבע TLS (JA3/JA4) - בדרך כלל הגורם המרכזי.** ספריית `requests`
   ב-Python מבצעת TLS handshake בסדר cipher suites/extensions שונה לגמרי
   מ-Chrome אמיתי. Incapsula/Imperva בודקות טביעת אצבע TLS **כשכבה נוספת לפני
   שהן בכלל מסתכלות על cookies** - כך שגם cookies תקפים במאה אחוז לא יעזרו
   אם ה-TLS handshake "נשמע" כמו סקריפט ולא כמו דפדפן.

**המשמעות המעשית:** אי אפשר לנתק לגמרי בין "חילוץ cookies" (בדפדפן) לבין
"שימוש בהם" (ב-`requests` רגיל) מול הגנה אמיתית של Incapsula. `authenticated_requests.py`
עדיין שימושי מול שרתים שבודקים cookies בלבד (או ללימוד/מעבדה מקומית כמו
`waf-proxy/proxy.py` בתיקייה הזו), אבל מול Incapsula אמיתית עם הגנת
fingerprint מלאה, שתי גישות עובדות טוב יותר:

- **המשך להשתמש באותו תהליך דפדפן** שהנפיק את ה-cookies כדי גם לגלוש בתוכן
  (`stealth_browser_bypass.py` כבר יכול לשמור HTML - זה עוקף את כל בעיית
  ה-fingerprint כי אותו דפדפן ממשיך את אותו session).
- אם חובה להשתמש ב-`requests`/`httpx`, ודא שהוא **רץ דרך אותו IP/פרוקסי**
  בדיוק שממנו הופק ה-cookie, והשתמש בספרייה שמדמה TLS fingerprint של Chrome
  (כמו `curl_cffi` עם `impersonate="chrome120"`, או `tls-client`) במקום
  `requests` הרגיל.

### בעיה: Connection Refused

**סיבות:**
1. URL לא נכון
2. האתר down
3. Firewall/Proxy חוסם

**פתרון:**
```bash
# בדוק שה-URL עובד
curl https://target.com

# אם URL צריך HTTPS, תוכן קודם:
python3 tools/stealth_browser_bypass.py https://target.com
```

### בעיה: Cookies מסתיימים מהר

**סיבה:** Incapsula מוגבל לזמן מוגבל (בדרך כלל 5-60 דקות)

**פתרון:** תוך התהליך האחרון:
```python
while True:
    # נסה להשתמש בcookies
    result = auth.get('/')
    
    if result['status'] == 403:
        print("Cookies expired, getting new ones...")
        # קבל cookies חדשים עם browser bypass
        break
    
    # עשה משהו עם התוכן
    process_content(result['content'])
```

---

## Header שימושיים

אם אתה חושב שחסרים headers, הוסף אותם:

```python
from authenticated_requests import AuthenticatedRequests

auth = AuthenticatedRequests(...)

# GET עם headers מותאמים
result = auth.get('/api/data', headers={
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://target.com/',
    'Authorization': 'Bearer TOKEN'
})
```

---

## זרימה מלאה

```bash
#!/bin/bash

# שלב 1: קבל cookies עם browser
echo "1. Getting cookies with browser bypass..."
python3 tools/stealth_browser_bypass.py https://target.com \
  --json-output cookies.json

# שלב 2: שחזור cookies
echo "2. Extracting cookies from JSON..."
VISID=$(jq -r '.cookies[] | select(.name | startswith("visid_incap")) | .value' cookies.json)
INCAP=$(jq -r '.cookies[] | select(.name | startswith("incap_ses")) | .value' cookies.json)

# שלב 3: השתמש בcookies
echo "3. Making authenticated request..."
python3 tools/authenticated_requests.py \
  https://target.com \
  "$VISID" \
  "$INCAP" \
  --output result.html

echo "✓ Done! Check result.html"
```

---

## אחת שורה (Quick Start)

```bash
# Get cookies + Access + Save (הכל בשורה אחת)
python3 tools/stealth_browser_bypass.py https://target.com --json-output c.json && \
VISID=$(jq -r '.cookies[0].value' c.json) && \
INCAP=$(jq -r '.cookies[1].value' c.json) && \
python3 tools/authenticated_requests.py https://target.com "$VISID" "$INCAP" --output result.html && \
echo "✓ Done!"
```

---

## סיכום

| צעד | פקודה | מטרה |
|-----|--------|--------|
| 1. קבל cookies | `stealth_browser_bypass.py` | חלוץ WAF |
| 2. שחזר cookies | `jq` או `json.load()` | קח את הערכים |
| 3. גשר עם cookies | `authenticated_requests.py` | כנס לאתר |
| 4. שמור תוכן | `--output result.html` | שמור דטה |

**כן, זה כל מה שצריך!** 🎯

