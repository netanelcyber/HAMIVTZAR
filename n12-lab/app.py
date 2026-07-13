#!/usr/bin/env python3
"""
HaMivtzar News Lab — an intentionally vulnerable practice target.

WHAT THIS IS
------------
A small, self-contained mock news portal that mimics the *architecture* of a
real Israeli news site (news lobby, live "writers chat" feed, weather feed,
search, a feed loader, a recommendation proxy, an admin panel). It is built
for LEGAL security-testing practice against infrastructure YOU own and run
locally — the same idea as DVWA / OWASP Juice Shop.

It is NOT a clone of any real site: branding is generic, content is fictional,
and a loud banner marks it as a training lab.

HOW TO RUN
----------
    python3 app.py            # serves on http://127.0.0.1:8099
    HOST=127.0.0.1 PORT=8099 python3 app.py

Then attack it freely. See attacks/SOLUTIONS.md for the intended findings and
attacks/SCRIPT_ANALYSIS.md for the JS-deobfuscation exercise.

Zero third-party dependencies — Python standard library only.

The intentional weaknesses are tagged inline as  # [VULN-xx].  They exist on
purpose. DO NOT copy this code into a real application.
"""

import html
import json
import os
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import seed

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8099"))
FEEDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feeds")

# Weak/default admin creds, no lockout -> brute-force practice.  # [VULN-08]
ADMIN_USER = "admin"
ADMIN_PASS = "admin"


# --------------------------------------------------------------------------
# HTML rendering helpers (kept deliberately simple)
# --------------------------------------------------------------------------
BANNER = (
    '<div style="background:#b00020;color:#fff;padding:10px 16px;'
    'font-family:sans-serif;text-align:center;font-weight:bold">'
    '⚠️ HaMivtzar News LAB — סביבת תרגול פגיעה בכוונה. לוקאלית בלבד. '
    'אל תפרסמו ואל תשתמשו נגד מערכת אמיתית.</div>'
)

PAGE_CSS = """
<style>
 body{font-family:Arial, sans-serif;margin:0;background:#f4f4f5;color:#1a1a1a;direction:rtl}
 header.top{background:#121214;color:#fff;padding:12px 20px;display:flex;
   justify-content:space-between;align-items:center}
 header.top .logo{font-size:22px;font-weight:bold;color:#db0000}
 nav{background:#fff;border-bottom:1px solid #ddd;padding:8px 20px}
 nav a{margin-left:14px;color:#333;text-decoration:none;font-size:14px}
 main{max-width:1000px;margin:16px auto;display:grid;
   grid-template-columns:2fr 1fr;gap:16px;padding:0 16px}
 .teaser{background:#fff;border:1px solid #e5e5e5;padding:12px;margin-bottom:12px}
 .teaser h3{margin:0 0 6px}
 .teaser a{color:#111;text-decoration:none}
 .teaser small{color:#777}
 aside{background:#fff;border:1px solid #e5e5e5;padding:12px}
 aside h4{margin-top:0;color:#db0000}
 .msg{border-bottom:1px solid #eee;padding:6px 0;font-size:14px}
 .msg .who{font-weight:bold}
 form.search{margin:0}
 footer{max-width:1000px;margin:24px auto;padding:16px;color:#888;font-size:13px}
 code{background:#eee;padding:1px 4px;border-radius:3px}
</style>
"""


def page(title, body):
    return (
        "<!doctype html><html lang='he'><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>{PAGE_CSS}</head><body>"
        f"{BANNER}"
        "<header class='top'><span class='logo'>מבצר 12 · News LAB</span>"
        "<form class='search' action='/newssearch'>"
        "<input name='q' placeholder='חיפוש בלאב'>"
        "<button>חפש</button></form></header>"
        "<nav>"
        "<a href='/'>לובי</a>"
        "<a href='/newssearch?q=חדשות'>חיפוש</a>"
        "<a href='/AjaxPage?jspName=weather.json&type=weather'>מזג אוויר (feed)</a>"
        "<a href='/config/version'>version</a>"
        "<a href='/admin'>admin</a>"
        "<a href='/static/hb-loader.js'>hb-loader.js (RE)</a>"
        "</nav>"
        f"{body}"
        "<footer>HaMivtzar News Lab · target תרגול מקומי · "
        "ראו <code>attacks/SOLUTIONS.md</code></footer>"
        "</body></html>"
    )


def render_lobby():
    teasers = ""
    for a in seed.ARTICLES:
        if not a["published"]:
            continue  # drafts are not linked (but see the IDOR endpoint)
        teasers += (
            "<div class='teaser'>"
            f"<h3><a href='/article?id={a['id']}'>{html.escape(a['title'])}</a></h3>"
            f"<small>{html.escape(a['author'])} | {html.escape(a['time'])}</small>"
            "</div>"
        )
    chat = "<aside><h4>צ'אט הכתבים (חי)</h4><div id='chat'>" + render_chat_html() + "</div>"
    chat += (
        "<form method='post' action='/api/chat' style='margin-top:10px'>"
        "<input name='reporter' placeholder='כתב/ת'> "
        "<input name='text' placeholder='הודעה'> <button>שלח</button></form></aside>"
    )
    # The obfuscated header-bidding-style loader is referenced here as an
    # in-lab reverse-engineering challenge (see attacks/SCRIPT_ANALYSIS.md).
    scr = "<script src='/static/hb-loader.js'></script>"
    return page("מבצר 12 · News LAB", "<main><section>" + teasers + "</section>" + chat + "</main>" + scr)


def render_chat_html():
    out = ""
    for m in seed.CHAT_MESSAGES:
        # [VULN-05] stored XSS: message text is inserted WITHOUT escaping.
        out += (
            "<div class='msg'>"
            f"<span class='who'>{html.escape(m['reporter'])}</span> "
            f"<small>{html.escape(m['time'])}</small><br>{m['text']}</div>"
        )
    return out


# --------------------------------------------------------------------------
# Request handler
# --------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "HaMivtzarLab/1.2"  # [VULN-07] version disclosure via header

    # -- small response helpers --
    def _send(self, code, body, ctype="text/html; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # [VULN-06] NOTE: no CSP, no X-Frame-Options, no X-Content-Type-Options.
        # (A hardened app would set them here.)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False, indent=2),
                   ctype="application/json; charset=utf-8")

    def log_message(self, fmt, *args):
        # concise request log so you can watch your own attacks land
        print("[req] %s - %s" % (self.address_string(), fmt % args))

    # ---- routing ----
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            return self._send(200, render_lobby())
        if path == "/newssearch":
            return self.route_search(qs)
        if path == "/article":
            return self.route_article(qs)
        if path == "/AjaxPage":
            return self.route_ajaxpage(qs)
        if path == "/api/chat":
            return self._json(200, {"messages": seed.CHAT_MESSAGES})
        if path == "/proxy/multivac":
            return self.route_proxy(qs)
        if path == "/go":
            return self.route_redirect(qs)
        if path == "/config/version" or path == "/eudaapi/version":
            return self.route_version()
        if path == "/.env":
            return self.route_dotenv()
        if path == "/admin":
            return self.route_admin(qs)
        if path.startswith("/static/"):
            return self.route_static(path)
        return self._send(404, page("404", "<main><section>404 — לא נמצא</section></main>"))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8", "replace")
        form = {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}
        if parsed.path == "/api/chat":
            return self.route_chat_post(form)
        return self._send(404, page("404", "<main><section>404</section></main>"))

    # ---- individual routes ----
    def route_search(self, qs):
        q = (qs.get("q", [""])[0] or qs.get("searchstring_input", [""])[0])
        fmt = qs.get("fmt", ["html"])[0]
        matches = [a for a in seed.ARTICLES
                   if a["published"] and q and q in (a["title"] + a["body"])]
        if fmt == "json":
            return self._json(200, {"query": q, "results": matches})
        # [VULN-01] reflected XSS: `q` echoed into HTML WITHOUT escaping.
        rows = "".join(
            f"<div class='teaser'><a href='/article?id={a['id']}'>"
            f"{html.escape(a['title'])}</a></div>" for a in matches
        ) or "<p>אין תוצאות.</p>"
        body = (
            "<main><section>"
            f"<h2>תוצאות חיפוש עבור: {q}</h2>"   # <-- unescaped on purpose
            f"{rows}</section></main>"
        )
        return self._send(200, page("חיפוש", body))

    def route_article(self, qs):
        try:
            aid = int(qs.get("id", ["0"])[0])
        except ValueError:
            return self._send(400, page("400", "<main><section>bad id</section></main>"))
        art = next((a for a in seed.ARTICLES if a["id"] == aid), None)
        if not art:
            return self._send(404, page("404", "<main><section>כתבה לא נמצאה</section></main>"))
        # [VULN-02] IDOR / broken access control: unpublished drafts are served
        # by direct id even though they are never linked from the lobby, and the
        # internal editor note is leaked too.
        note = ""
        if not art["published"]:
            note = ("<p style='color:#b00020'><b>טיוטה לא מפורסמת שנחשפה!</b><br>"
                    f"internal: <code>{html.escape(art['internal'])}</code></p>")
        body = (
            "<main><section><article>"
            f"<h1>{html.escape(art['title'])}</h1>"
            f"<small>{html.escape(art['author'])} | {html.escape(art['time'])}</small>"
            f"<p>{html.escape(art['body'])}</p>{note}"
            "</article></section></main>"
        )
        return self._send(200, page(art["title"], body))

    def route_ajaxpage(self, qs):
        # Mimics the real portal's `/AjaxPage?jspName=...` feed loader.
        name = qs.get("jspName", ["weather.json"])[0]
        # [VULN-03] path traversal / LFI: `jspName` is joined to FEEDS_DIR with
        # no sanitization, so `../../etc/passwd` (or ../feeds/SECRET*) escapes.
        target = os.path.join(FEEDS_DIR, name)
        try:
            with open(target, "rb") as fh:
                data = fh.read()
        except OSError:
            return self._json(404, {"error": "feed not found", "jspName": name})
        ctype = "application/json" if name.endswith(".json") else "text/plain"
        return self._send(200, data, ctype=ctype + "; charset=utf-8")

    def route_proxy(self, qs):
        # Mimics an Outbrain-Multivac-style recommendation proxy: ?url=...
        url = qs.get("url", [""])[0]
        if not url:
            return self._json(400, {"error": "missing url"})
        # [VULN-04] SSRF: the server fetches an arbitrary attacker-supplied URL.
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "HaMivtzarLab-proxy"})
            with urllib.request.urlopen(req, timeout=4) as r:   # nosec - lab
                body = r.read(4096)
            return self._send(200, body, ctype="text/plain; charset=utf-8")
        except Exception as e:  # noqa: BLE001 - lab: surface the error verbosely
            return self._json(502, {"error": str(e), "url": url})  # [VULN-07] verbose

    def route_redirect(self, qs):
        # Mimics the site's `?partner=`/mobile-redirect logic.
        dest = qs.get("url", [qs.get("partner", ["/"])[0]])[0]
        # [VULN-09] open redirect: no allow-list on the destination.
        return self._send(302, "", extra={"Location": dest})

    def route_version(self):
        # [VULN-07] info disclosure: dumps internal config, hostnames, fake key.
        return self._json(200, seed.INTERNAL_CONFIG)

    def route_dotenv(self):
        # [VULN-10] sensitive file exposure (a classic misconfig).
        body = ("APP=hamivtzar-news-lab\nDEBUG=true\n"
                "ADMIN_USER=admin\nADMIN_PASS=admin\n"
                "SECRET_KEY=LAB_FAKE_SECRET_0000\n"
                "INTERNAL_HOST=int-adm-01.lab.internal\n")
        return self._send(200, body, ctype="text/plain; charset=utf-8")

    def route_admin(self, qs):
        user = qs.get("user", [""])[0]
        pw = qs.get("pass", [""])[0]
        if user == ADMIN_USER and pw == ADMIN_PASS:  # [VULN-08] weak/default, no lockout
            drafts = "".join(
                f"<li>#{a['id']} — {html.escape(a['title'])}</li>"
                for a in seed.ARTICLES if not a["published"]
            )
            body = ("<main><section><h2>Admin — פאנל ניהול</h2>"
                    f"<p>מחובר כ-<b>{html.escape(user)}</b>.</p>"
                    f"<h3>טיוטות תחת אמברגו</h3><ul>{drafts}</ul></section></main>")
            return self._send(200, page("admin", body))
        body = ("<main><section><h2>Admin login</h2>"
                "<form method='get' action='/admin'>"
                "<input name='user' placeholder='user'> "
                "<input name='pass' type='password' placeholder='pass'> "
                "<button>כניסה</button></form>"
                "<p style='color:#777'>רמז: זו סביבת תרגול...</p></section></main>")
        return self._send(401, page("admin", body))

    def route_chat_post(self, form):
        reporter = form.get("reporter", "אנונימי")[:40] or "אנונימי"
        text = form.get("text", "")
        # [VULN-05] stored XSS: text is stored raw and later rendered unescaped.
        seed.CHAT_MESSAGES.insert(0, {
            "id": 6000 + len(seed.CHAT_MESSAGES),
            "reporter": reporter,
            "time": "now",
            "text": text,  # <-- not sanitized
        })
        return self._send(302, "", extra={"Location": "/"})

    def route_static(self, path):
        name = path[len("/static/"):]
        if name == "hb-loader.js":
            return self._send(200, OBFUSCATED_JS,
                              ctype="application/javascript; charset=utf-8")
        if name == "style.css":
            return self._send(200, "/* see inline PAGE_CSS */",
                              ctype="text/css; charset=utf-8")
        return self._send(404, "not found", ctype="text/plain")


# --------------------------------------------------------------------------
# An obfuscated "header-bidding loader" served by the lab, using the SAME
# string-array-rotation trick as the real site's VAD/header-bidding snippet.
# This is the reverse-engineering challenge; attacks/deobfuscate.py + the
# writeup explain and undo it. (It is harmless: it only console.logs.)
# --------------------------------------------------------------------------
OBFUSCATED_JS = r"""
var _0x3f21=['log','ready','init','loader','HaMivtzar','LAB','publisher','n-lab'];
(function(_0x1,_0x2){var _0x3=function(_0x4){while(--_0x4){_0x1['push'](_0x1['shift']());}};
_0x3(++_0x2);}(_0x3f21,0x1a));
var _0x9a=function(_0x1,_0x2){_0x1=_0x1-0x0;return _0x3f21[_0x1];};
(function(){var name=_0x9a('0x2')+' '+_0x9a('0x1');
console[_0x9a('0x6')]('['+name+'] '+_0x9a('0x0')+' for '+_0x9a('0x4')+' '+_0x9a('0x5'));})();
"""


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"HaMivtzar News Lab serving on http://{HOST}:{PORT}  (Ctrl-C to stop)")
    print("Intentionally vulnerable. Local practice only.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
