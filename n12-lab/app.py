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
 article{background:#fff;border:1px solid #e5e5e5;padding:16px}
 article h1{margin-top:0}
 section.related,section.comments{background:#fff;border:1px solid #e5e5e5;
   padding:12px;margin-top:12px}
 section.related h3,section.comments h3{margin-top:0;color:#db0000}
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
        "<a href='/article?id=1001'>כתבה</a>"
        "<a href='/newssearch?q=חדשות'>חיפוש</a>"
        "<a href='/xss'>XSS playground</a>"
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
        if path == "/xss":
            return self.route_xss_index()
        if path == "/profile":
            return self.route_profile(qs)
        if path == "/greet":
            return self.route_greet(qs)
        if path == "/filtered":
            return self.route_filtered(qs)
        if path == "/welcome":
            return self.route_welcome()
        if path == "/article":
            return self.route_article(qs)
        if path == "/AjaxPage":
            return self.route_ajaxpage(qs)
        if path == "/api/chat":
            return self._json(200, {"messages": seed.CHAT_MESSAGES})
        if path == "/api/comments":
            return self.route_comments_get(qs)
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

    # HEAD mirrors GET routing; _send() suppresses the body when command==HEAD,
    # so scanners that probe with HEAD get real status codes and headers.
    do_HEAD = do_GET

    def do_POST(self):
        # [VULN-17] CSRF: none of the state-changing POST endpoints below check
        # a CSRF token, Origin, or Referer, so any site can forge chat/comment
        # writes in a logged-in victim's browser (wormable with the stored XSS).
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8", "replace")
        form = {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}
        if parsed.path == "/api/chat":
            return self.route_chat_post(form)
        if parsed.path == "/api/comments":
            return self.route_comments_post(form)
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

    # ---- XSS practice playground (multiple injection contexts) ----
    def route_xss_index(self):
        body = (
            "<main><section><h2>XSS playground</h2>"
            "<p>אותה פגיעות, הקשרים שונים — לכל אחד צריך payload אחר. "
            "פתרונות ב-<code>attacks/XSS_LAB.md</code>.</p>"
            "<ul>"
            "<li><a href='/newssearch?q=test'>reflected — HTML text</a> "
            "(VULN-01)</li>"
            "<li><a href='/profile?name=guest'>profile — HTML attribute</a> "
            "(VULN-12)</li>"
            "<li><a href='/greet?msg=hi'>greet — JavaScript string</a> "
            "(VULN-13)</li>"
            "<li><a href='/filtered?q=test'>filtered — naive WAF bypass</a> "
            "(VULN-14)</li>"
            "<li><a href='/welcome'>welcome — DOM-based (#fragment)</a> "
            "(VULN-15)</li>"
            "<li>stored: <code>POST /api/chat</code> (VULN-05), "
            "<code>POST /api/comments</code> (VULN-11)</li>"
            "</ul></section></main>"
        )
        return self._send(200, page("xss playground", body))

    def route_profile(self, qs):
        name = qs.get("name", ["guest"])[0]
        # [VULN-12] XSS in HTML ATTRIBUTE context: `name` is dropped inside a
        # double-quoted attribute value without escaping quotes, so a payload
        # like  " autofocus onfocus=alert(1) x="  breaks out of the attribute.
        body = (
            "<main><section><h2>הפרופיל שלי</h2>"
            "<form action='/profile'>"
            f"<input name='name' value=\"{name}\"> "  # <-- unescaped attribute
            "<button>עדכן</button></form>"
            f"<p>שלום, {html.escape(name)}!</p>"
            "</section></main>"
        )
        return self._send(200, page("profile", body))

    def route_greet(self, qs):
        msg = qs.get("msg", ["hi"])[0]
        # [VULN-13] XSS in JAVASCRIPT string context: `msg` is concatenated into
        # an inline <script> as a single-quoted string with no escaping, so
        #   ';alert(1);//   breaks out of the string and runs code.
        body = (
            "<main><section><h2>ברכה</h2>"
            "<div id='out'></div>"
            f"<script>var m='{msg}';"  # <-- unescaped into JS
            "document.getElementById('out').textContent='msg: '+m;</script>"
            "</section></main>"
        )
        return self._send(200, page("greet", body))

    def route_filtered(self, qs):
        q = qs.get("q", [""])[0]
        # [VULN-14] naive blocklist filter: strips only the literal lowercase
        # "<script" / "</script>". Trivially bypassed with a case variant
        # (<ScRiPt>) or an event-handler tag (<img src=x onerror=alert(1)>).
        filtered = q.replace("<script", "").replace("</script>", "")
        body = (
            "<main><section>"
            f"<h2>חיפוש מסונן: {filtered}</h2>"  # <-- post-filter, still injectable
            "<p style='color:#777'>ה-\"WAF\" הנאיבי מסיר רק "
            "<code>&lt;script</code> באותיות קטנות.</p>"
            "</section></main>"
        )
        return self._send(200, page("filtered", body))

    def route_welcome(self):
        # [VULN-15] DOM-based XSS: the URL fragment (location.hash) is written
        # into the page via innerHTML entirely client-side. The server never
        # sees the payload (it's after the '#'), so this is a pure client sink.
        body = (
            "<main><section><h2>ברוכים הבאים</h2>"
            "<div id='banner'>טוען...</div>"
            "<script>\n"
            "  var frag = decodeURIComponent(location.hash.slice(1));\n"
            "  // sink: innerHTML from the attacker-controlled fragment\n"
            "  document.getElementById('banner').innerHTML = frag || 'שלום אורח';\n"
            "</script>"
            "<p style='color:#777'>נסו: <code>/welcome#&lt;img src=x "
            "onerror=alert(1)&gt;</code></p>"
            "</section></main>"
        )
        return self._send(200, page("welcome", body))

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

        # Article body with an in-content ad slot between paragraphs — this is
        # where the real page injects its header-bidding/googletag slots.
        paras = art.get("paragraphs") or [art["body"]]
        body_html = ""
        for i, p in enumerate(paras):
            body_html += f"<p>{html.escape(p)}</p>"
            if i == 0:  # in-content ad slot after the lead paragraph
                body_html += (
                    "<div class='adslot' style='background:#faf7e6;border:1px dashed #cdb;"
                    "padding:14px;margin:12px 0;color:#987;text-align:center'>"
                    "מודעה (ad slot) — vad-hb</div>"
                )

        related = self.render_related(art.get("related", []))
        comments = self.render_comments_html(aid)
        comment_form = (
            "<form method='post' action='/api/comments' style='margin-top:12px'>"
            f"<input type='hidden' name='articleId' value='{aid}'>"
            "<input name='name' placeholder='שם'> "
            "<input name='text' placeholder='כתבו תגובה'> "
            "<button>פרסמו תגובה</button></form>"
        )

        article_html = (
            "<article>"
            f"<h1>{html.escape(art['title'])}</h1>"
            f"<small>{html.escape(art['author'])} | {html.escape(art['time'])}</small>"
            f"{body_html}{note}"
            "</article>"
            "<section class='related'><h3>עוד בלאב</h3>" + related + "</section>"
            "<section class='comments'><h3>תגובות</h3>"
            f"<div id='comments'>{comments}</div>{comment_form}</section>"
        )
        # The article's own obfuscated header-bidding loader (2nd RE challenge).
        scr = "<script src='/static/vad-hb.js'></script>"
        body = "<main><section>" + article_html + "</section>" + self.render_article_aside() + "</main>" + scr
        return self._send(200, page(art["title"], body))

    def render_related(self, ids):
        out = ""
        for rid in ids:
            a = next((x for x in seed.ARTICLES if x["id"] == rid and x["published"]), None)
            if not a:
                continue
            out += (
                "<div class='teaser'>"
                f"<a href='/article?id={a['id']}'>{html.escape(a['title'])}</a></div>"
            )
        return out or "<p>אין המלצות.</p>"

    def render_article_aside(self):
        # A recommendation strip fed through the (SSRF-able) multivac proxy, so
        # the article page exercises the same rec-proxy surface as the real page.
        return (
            "<aside><h4>מומלצים עבורכם</h4>"
            "<p style='font-size:13px;color:#777'>נטען דרך "
            "<code>/proxy/multivac?url=…</code></p>"
            "<div class='adslot' style='background:#faf7e6;border:1px dashed #cdb;"
            "padding:20px;text-align:center;color:#987'>מודעה (side)</div>"
            "</aside>"
        )

    def render_comments_html(self, aid):
        out = ""
        for c in seed.COMMENTS.get(aid, []):
            # [VULN-11] stored XSS: comment text is rendered WITHOUT escaping,
            # a second stored-XSS sink distinct from the writers-chat one.
            out += (
                "<div class='msg'>"
                f"<span class='who'>{html.escape(c['name'])}</span> "
                f"<small>{html.escape(c['time'])}</small><br>{c['text']}</div>"
            )
        return out or "<p style='color:#777'>אין תגובות עדיין.</p>"

    def route_comments_get(self, qs):
        try:
            aid = int(qs.get("articleId", ["0"])[0])
        except ValueError:
            return self._json(400, {"error": "bad articleId"})
        # [VULN-11 pairs with VULN-02] no check that the article is published,
        # so comments on the embargoed draft (id 1999) are listable too.
        return self._json(200, {"articleId": aid,
                                "comments": seed.COMMENTS.get(aid, [])})

    def route_comments_post(self, form):
        try:
            aid = int(form.get("articleId", "0"))
        except ValueError:
            return self._json(400, {"error": "bad articleId"})
        name = (form.get("name", "אנונימי/ת")[:40] or "אנונימי/ת")
        text = form.get("text", "")
        # [VULN-11] stored XSS: comment body stored raw, later rendered unescaped.
        # No auth, no article-published check -> also lets you seed comments onto
        # unpublished drafts (IDOR).
        seed.COMMENTS.setdefault(aid, []).append({
            "id": 7000 + sum(len(v) for v in seed.COMMENTS.values()),
            "name": name,
            "time": "now",
            "text": text,  # <-- not sanitized
        })
        return self._send(302, "", extra={"Location": f"/article?id={aid}"})

    def route_ajaxpage(self, qs):
        # Mimics the real portal's `/AjaxPage?jspName=...` feed loader.
        name = qs.get("jspName", ["weather.json"])[0]
        # [VULN-03] path traversal / LFI: `jspName` is joined to FEEDS_DIR with
        # no sanitization, so `../../etc/passwd` (or ../feeds/SECRET*) escapes.
        # NOTE (red-team): even stronger than it looks — os.path.join(base, ABS)
        # DISCARDS `base`, so jspName=/etc/passwd is a direct arbitrary-file read
        # with no `../` at all, including this app's own source.
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
        # NOTE (red-team): urlopen also honours file:// -> a second arbitrary-read
        # primitive (file:///etc/passwd). And the verbose error below is a
        # port-scan oracle (Connection refused vs. a real body maps internal svc).
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
        # [VULN-16] CRLF / HTTP response-header injection: `dest` is passed raw
        # into the Location header, so a payload containing %0d%0a splits the
        # response and injects arbitrary headers (e.g. Set-Cookie -> session
        # fixation, or cache-poisoning). Far worse than a plain open redirect.
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
        if name == "vad-hb.js":
            return self._send(200, VAD_OBFUSCATED_JS,
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


# --------------------------------------------------------------------------
# The ARTICLE page's obfuscated "VAD / header-bidding" loader, served at
# /static/vad-hb.js. It uses the exact same string-array-rotation trick as the
# real page's `var _0x2050=[...]` snippet (generic branding: cdn.valuad.lab,
# publisher n-lab). Same deobfuscate.py decodes it. When resolved it just shows
# a googletag/header-bidding script injector — see attacks/vad-hb-snippet.js.
# --------------------------------------------------------------------------
VAD_OBFUSCATED_JS = r"""
var _0x2050=['type','head','document','createElement','script','src','//cdn.valuad.lab/hb/loader.js','setAttribute','data-publisher','n-lab','appendChild','text/javascript','_vadHb','push','now','random','googletag','cmd','pubads','disableInitialLoad'];
(function(_0xa,_0xb){var _0xc=function(_0xd){while(--_0xd){_0xa['push'](_0xa['shift']());}};_0xc(++_0xb);}(_0x2050,0xb));
var _0x48=function(_0xa,_0xb){_0xa=_0xa-0x0;return _0x2050[_0xa];};
(function(){
  var _d = window[_0x48('0xb')];
  var _s = _d[_0x48('0xc')](_0x48('0xd'));
  _s[_0x48('0x9')] = _0x48('0x0');
  _s[_0x48('0xe')] = _0x48('0xf');
  _s[_0x48('0x10')](_0x48('0x11'), _0x48('0x12'));
  _d[_0x48('0xa')][_0x48('0x13')](_s);
  window[_0x48('0x1')] = window[_0x48('0x1')] || [];
  window[_0x48('0x1')][_0x48('0x2')]({ ts: Date[_0x48('0x3')](), rnd: Math[_0x48('0x4')]() });
  (window[_0x48('0x5')] = window[_0x48('0x5')] || {})[_0x48('0x6')] =
      window[_0x48('0x5')][_0x48('0x6')] || [];
  window[_0x48('0x5')][_0x48('0x6')][_0x48('0x2')](function(){
      window[_0x48('0x5')][_0x48('0x7')]()[_0x48('0x8')]();
  });
})();
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
