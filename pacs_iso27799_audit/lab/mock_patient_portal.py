"""A tiny, local, loopback-only mock of a patient self-service login pattern.

This is NOT a copy of any real product's code, branding, or visual design --
it deliberately mimics only the *functional* shape of one narrow pattern
(a two-field patient self-service login: date of birth + a short secondary
access code, submitted as a normal HTML form POST) because that shape is
what determines the security properties controls AC-6/AC-7/OPS-5 in
../controls.py are checking. There is no product name, logo, or copyright
text here to copy, and there won't be -- a visually convincing replica of a
real login page has no testing value and is exactly the shape of a phishing
page, so this stays a plain, clearly-labeled lab form.

Since the real class of app this rehearses against is commonly built on
ASP.NET WebForms, this mock also models the operationally relevant part of
that framework's postback pattern: a GET issues a short-lived, single-use
token pair (named __VIEWSTATE/__EVENTVALIDATION after the real field names,
since those are just field-name conventions, not anything copyrightable)
that a POST must present. This is NOT a reimplementation of ASP.NET's actual
ViewState/EventValidation algorithm (which MACs serialized page state against
a machine key) -- it only reproduces the behavior that matters for this
rehearsal: an attacker script must fetch a fresh token before every guess,
which is a real (mild) speed bump against naive brute-force automation.

Safety property: this server only ever binds to 127.0.0.1. There is no flag
to change that -- if you need it reachable from elsewhere, you have made a
decision this script deliberately does not support.

Usage:
    python -m pacs_iso27799_audit.lab.mock_patient_portal
    python -m pacs_iso27799_audit.lab.mock_patient_portal --no-rate-limit
    python -m pacs_iso27799_audit.lab.mock_patient_portal --lockout-threshold 3 --lockout-window-seconds 30
    python -m pacs_iso27799_audit.lab.mock_patient_portal --no-postback-tokens
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import random
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Tuple
from urllib.parse import parse_qs

# Field names match the two-field shape (date of birth + short access code)
# used by this class of patient self-service login -- functional fidelity
# only, not a claim about any specific product's exact wire format.
FIELD_DOB = "patient_birth_date"
FIELD_CODE = "user_code"
FIELD_VIEWSTATE = "__VIEWSTATE"
FIELD_EVENTVALIDATION = "__EVENTVALIDATION"

DEMO_DOB = "1990-01-01"  # intentionally "public" in this lab -- the point is DOB alone is weak
CODE_SPACE = 1000  # 3-digit code, small on purpose so a demo brute force finishes quickly
TOKEN_TTL_SECONDS = 120.0


class _State:
    def __init__(
        self,
        rate_limit_enabled: bool,
        lockout_threshold: int,
        lockout_window_seconds: float,
        postback_tokens_enabled: bool = True,
    ):
        self.access_code = f"{random.randint(0, CODE_SPACE - 1):03d}"
        self.rate_limit_enabled = rate_limit_enabled
        self.lockout_threshold = lockout_threshold
        self.lockout_window_seconds = lockout_window_seconds
        self.postback_tokens_enabled = postback_tokens_enabled
        self.lock = threading.Lock()
        # dob -> (failure_count, window_started_at, locked_until)
        # Keyed on the "identifying" field, same as a real deployment should
        # lock out per patient record rather than only per source IP.
        self.failures: Dict[str, Tuple[int, float, float]] = {}
        self._server_secret = secrets.token_bytes(32)
        # viewstate -> (expiry, used)
        self._tokens: Dict[str, Tuple[float, bool]] = {}

    def issue_token(self) -> Tuple[str, str]:
        viewstate = secrets.token_urlsafe(24)
        eventvalidation = hmac.new(self._server_secret, viewstate.encode(), hashlib.sha256).hexdigest()
        with self.lock:
            self._tokens[viewstate] = (time.monotonic() + TOKEN_TTL_SECONDS, False)
        return viewstate, eventvalidation

    def consume_token(self, viewstate: str, eventvalidation: str) -> bool:
        expected = hmac.new(self._server_secret, viewstate.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, eventvalidation or ""):
            return False
        with self.lock:
            entry = self._tokens.get(viewstate)
            if entry is None:
                return False
            expiry, used = entry
            if used or time.monotonic() > expiry:
                return False
            self._tokens[viewstate] = (expiry, True)  # single-use
            return True

    def check(self, dob: str, access_code: str) -> Tuple[int, dict]:
        now = time.monotonic()
        with self.lock:
            count, window_start, locked_until = self.failures.get(dob, (0, now, 0.0))

            if self.rate_limit_enabled and now < locked_until:
                return 429, {"error": "locked_out", "retry_after_seconds": round(locked_until - now, 1)}

            if dob != DEMO_DOB or access_code != self.access_code:
                if now - window_start > self.lockout_window_seconds:
                    count, window_start = 0, now
                count += 1
                locked_until = 0.0
                if self.rate_limit_enabled and count >= self.lockout_threshold:
                    locked_until = now + self.lockout_window_seconds
                self.failures[dob] = (count, window_start, locked_until)
                return 401, {"error": "invalid_credentials"}

            self.failures.pop(dob, None)
            return 200, {"status": "ok", "message": "demo exam summary unlocked"}


def _make_handler(state: _State):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # keep test-run output quiet; nothing sensitive is logged anyway

        def _write_json(self, status: int, payload: dict) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path != "/login":
                self.send_response(404)
                self.end_headers()
                return
            if not state.postback_tokens_enabled:
                self._write_json(200, {})
                return
            viewstate, eventvalidation = state.issue_token()
            self._write_json(200, {FIELD_VIEWSTATE: viewstate, FIELD_EVENTVALIDATION: eventvalidation})

        def do_POST(self):
            if self.path != "/instant-access":
                self.send_response(404)
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            fields = parse_qs(raw)

            if state.postback_tokens_enabled:
                valid = state.consume_token(
                    fields.get(FIELD_VIEWSTATE, [""])[0],
                    fields.get(FIELD_EVENTVALIDATION, [""])[0],
                )
                if not valid:
                    self._write_json(400, {"error": "invalid_or_expired_postback_token"})
                    return

            status, payload = state.check(
                fields.get(FIELD_DOB, [""])[0],
                fields.get(FIELD_CODE, [""])[0],
            )
            self._write_json(status, payload)

    return Handler


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--rate-limit", dest="rate_limit", action=argparse.BooleanOptionalAction, default=True,
                        help="Enable/disable lockout, to compare protected vs. unprotected behavior")
    parser.add_argument("--lockout-threshold", type=int, default=5)
    parser.add_argument("--lockout-window-seconds", type=float, default=60.0)
    parser.add_argument("--postback-tokens", dest="postback_tokens", action=argparse.BooleanOptionalAction,
                        default=True, help="Require a fresh GET /login token pair before each POST")
    args = parser.parse_args(argv)

    state = _State(args.rate_limit, args.lockout_threshold, args.lockout_window_seconds, args.postback_tokens)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), _make_handler(state))

    print(f"Mock patient self-service login (LAB ONLY) on http://127.0.0.1:{args.port}/instant-access")
    print(f"  form fields: {FIELD_DOB!r}, {FIELD_CODE!r} (application/x-www-form-urlencoded POST)")
    print(f"  demo {FIELD_DOB}={DEMO_DOB!r} ('known to the attacker' in this exercise)")
    print(f"  ground truth {FIELD_CODE}={state.access_code!r} (operator-only -- the rehearsal client must guess it)")
    print(f"  rate_limit={'enabled' if args.rate_limit else 'disabled'} "
          f"threshold={args.lockout_threshold} window={args.lockout_window_seconds}s")
    print(f"  postback_tokens={'enabled (GET /login first)' if args.postback_tokens else 'disabled'}")
    print("Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
