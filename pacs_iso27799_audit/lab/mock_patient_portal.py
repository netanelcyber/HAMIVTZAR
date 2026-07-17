"""A tiny, local, loopback-only mock of a patient self-service login pattern.

This is NOT a copy of any real product's code, UI, or branding -- it is a
generic stand-in for one narrow pattern: authenticating with a low-entropy
identifier (date of birth) plus a short secondary code, the kind of flow
controls AC-6/AC-7/OPS-5 in ../controls.py are about. It exists so the
brute-force / rate-limiting / lockout testing technique can be rehearsed
against something you run yourself.

Safety property: this server only ever binds to 127.0.0.1. There is no flag
to change that -- if you need it reachable from elsewhere, you have made a
decision this script deliberately does not support.

Usage:
    python -m pacs_iso27799_audit.lab.mock_patient_portal
    python -m pacs_iso27799_audit.lab.mock_patient_portal --no-rate-limit
    python -m pacs_iso27799_audit.lab.mock_patient_portal --lockout-threshold 3 --lockout-window-seconds 30
"""

from __future__ import annotations

import argparse
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Tuple

DEMO_USER_ID = "demo-patient"
DEMO_DOB = "1990-01-01"  # intentionally "public" in this lab -- the point is DOB alone is weak
CODE_SPACE = 1000  # 3-digit code, small on purpose so a demo brute force finishes quickly


class _State:
    def __init__(self, rate_limit_enabled: bool, lockout_threshold: int, lockout_window_seconds: float):
        self.access_code = f"{random.randint(0, CODE_SPACE - 1):03d}"
        self.rate_limit_enabled = rate_limit_enabled
        self.lockout_threshold = lockout_threshold
        self.lockout_window_seconds = lockout_window_seconds
        self.lock = threading.Lock()
        # user_id -> (failure_count, window_started_at, locked_until)
        self.failures: Dict[str, Tuple[int, float, float]] = {}

    def check(self, user_id: str, dob: str, access_code: str) -> Tuple[int, dict]:
        now = time.monotonic()
        with self.lock:
            count, window_start, locked_until = self.failures.get(user_id, (0, now, 0.0))

            if self.rate_limit_enabled and now < locked_until:
                return 429, {"error": "locked_out", "retry_after_seconds": round(locked_until - now, 1)}

            if user_id != DEMO_USER_ID or dob != DEMO_DOB or access_code != self.access_code:
                if now - window_start > self.lockout_window_seconds:
                    count, window_start = 0, now
                count += 1
                locked_until = 0.0
                if self.rate_limit_enabled and count >= self.lockout_threshold:
                    locked_until = now + self.lockout_window_seconds
                self.failures[user_id] = (count, window_start, locked_until)
                return 401, {"error": "invalid_credentials"}

            self.failures.pop(user_id, None)
            return 200, {"status": "ok", "message": "demo exam summary unlocked"}


def _make_handler(state: _State):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # keep test-run output quiet; nothing sensitive is logged anyway

        def do_POST(self):
            if self.path != "/instant-access":
                self.send_response(404)
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                body = {}

            status, payload = state.check(
                str(body.get("user_id", "")),
                str(body.get("dob", "")),
                str(body.get("access_code", "")),
            )
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--rate-limit", dest="rate_limit", action=argparse.BooleanOptionalAction, default=True,
                        help="Enable/disable lockout, to compare protected vs. unprotected behavior")
    parser.add_argument("--lockout-threshold", type=int, default=5)
    parser.add_argument("--lockout-window-seconds", type=float, default=60.0)
    args = parser.parse_args(argv)

    state = _State(args.rate_limit, args.lockout_threshold, args.lockout_window_seconds)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), _make_handler(state))

    print(f"Mock patient self-service portal (LAB ONLY) on http://127.0.0.1:{args.port}/instant-access")
    print(f"  demo user_id={DEMO_USER_ID!r} dob={DEMO_DOB!r} (both 'known to the attacker' in this exercise)")
    print(f"  ground truth access_code={state.access_code!r} (operator-only -- the rehearsal client must guess it)")
    print(f"  rate_limit={'enabled' if args.rate_limit else 'disabled'} "
          f"threshold={args.lockout_threshold} window={args.lockout_window_seconds}s")
    print("Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
