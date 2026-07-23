"""
Simplified Incapsula/Imperva-style WAF proxy, for a local lab you own.

This does NOT reproduce Incapsula's real detection logic (JA3/TLS
fingerprinting, the real `reese84`/`___utmvc` sensor scripts, etc. are
proprietary, obfuscated, and far more sophisticated). It reimplements the
publicly-documented *shape* of that model -- a cookie-gated challenge
(`incap_ses_*` / `visid_incap_*`), a JS-computed token, basic UA/header
heuristics, and per-IP-window rate limiting -- so the bypass techniques in
../tools/ (header/UA fixing, forging the token without a browser, and
headless-browser rendering) have something real and self-contained to
exercise, without ever touching a third party's infrastructure.
"""
import base64
import os
import secrets
import time
from collections import deque

from flask import Flask, request, make_response, Response
import requests

app = Flask(__name__)

BACKEND = os.environ.get("BACKEND_URL", "http://localhost:5001")
SALT_SHIFT = 7  # part of the token algorithm -- see tools/crack_cipher_client.py

SESSIONS = {}  # waf_sess -> {"nonce": str, "verified": bool, "fails": int}
RATE_WINDOW = deque()
RATE_LIMIT = 60
RATE_PERIOD = 10

BLOCKED_UA_MARKERS = ("headlesschrome", "phantomjs", "python-requests", "curl/")


def compute_token(nonce: str) -> str:
    """The "sensor" algorithm. A real client must run the JS in
    challenge_page() (or reimplement it, see tools/crack_cipher_client.py)
    to produce a value that matches this."""
    reversed_nonce = nonce[::-1]
    shifted = "".join(f"{(ord(c) + SALT_SHIFT) % 256:02x}" for c in nonce)
    return base64.b64encode(f"{reversed_nonce}|{shifted}".encode()).decode()


def rate_limited() -> bool:
    now = time.time()
    RATE_WINDOW.append(now)
    while RATE_WINDOW and now - RATE_WINDOW[0] > RATE_PERIOD:
        RATE_WINDOW.popleft()
    return len(RATE_WINDOW) > RATE_LIMIT


def incident_page(reason: str, status: int = 403) -> Response:
    body = (
        "<html><body style='font-family:sans-serif'>"
        f"<h2>Request unsuccessful. Incident ID: LAB-{secrets.token_hex(4)}</h2>"
        f"<p>reason: {reason}</p>"
        "</body></html>"
    )
    resp = make_response(body, status)
    resp.headers["X-Lab-Block-Reason"] = reason
    return resp


def challenge_page(nonce: str) -> Response:
    # Terse, renamed variables on purpose: this stands in for a real,
    # obfuscated bot-detection "sensor" script that a bypass would need to
    # read and reimplement, not for normal app code.
    js = (
        "(function(){"
        f"var n='{nonce}';"
        "var r=n.split('').reverse().join('');"
        "var s='';"
        "for(var i=0;i<n.length;i++){"
        f"var v=(n.charCodeAt(i)+{SALT_SHIFT})%256;"
        "s+=(v<=0xf?'0':'')+v.toString(16);"
        "}"
        "var t=btoa(r+'|'+s);"
        "document.cookie='incap_ses_lab='+t+'; path=/; max-age=3600';"
        "location.reload();"
        "})();"
    )
    html = (
        "<html><head><title>Please wait...</title></head>"
        f"<body>Checking your browser before access...<script>{js}</script></body></html>"
    )
    return make_response(html, 200)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def gate(path):
    ua = request.headers.get("User-Agent", "").lower()

    if rate_limited():
        return incident_page("rate-limit-exceeded", 429)
    if not request.headers.get("Accept-Language"):
        return incident_page("missing-accept-language-header")
    if any(marker in ua for marker in BLOCKED_UA_MARKERS):
        return incident_page("blocked-user-agent-signature")

    sess_id = request.cookies.get("waf_sess")
    if sess_id is None or sess_id not in SESSIONS:
        sess_id = secrets.token_hex(8)
        SESSIONS[sess_id] = {"nonce": secrets.token_hex(6), "verified": False, "fails": 0}

    session = SESSIONS[sess_id]

    if not session["verified"]:
        incap_cookie = request.cookies.get("incap_ses_lab")
        if incap_cookie and incap_cookie == compute_token(session["nonce"]):
            session["verified"] = True
        else:
            session["fails"] += 1
            if session["fails"] > 20:
                return incident_page("too-many-failed-challenge-attempts", 403)
            resp = challenge_page(session["nonce"])
            resp.set_cookie("waf_sess", sess_id, httponly=True, samesite="Lax")
            return resp

    try:
        upstream = requests.get(f"{BACKEND}/{path}", timeout=5)
    except requests.RequestException as exc:
        return incident_page(f"upstream-unreachable: {exc}", 502)

    resp = make_response(upstream.content, upstream.status_code)
    resp.headers["Content-Type"] = upstream.headers.get("Content-Type", "text/html")
    resp.set_cookie("waf_sess", sess_id, httponly=True, samesite="Lax")
    resp.set_cookie("visid_incap_lab", sess_id, max_age=86400, samesite="Lax")
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
