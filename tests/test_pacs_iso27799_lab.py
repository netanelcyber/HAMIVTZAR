"""Tests for the local, loopback-only patient-self-service-login rehearsal lab.

Runs the real mock HTTP server on 127.0.0.1 with an OS-assigned port, so this
never touches any real system or the network beyond loopback.
"""

import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pacs_iso27799_audit.lab.mock_patient_portal import DEMO_DOB, DEMO_USER_ID, _State, _make_handler
from pacs_iso27799_audit.lab.rehearse_lockout_check import _require_loopback


def _post(url, user_id, dob, code):
    body = json.dumps({"user_id": user_id, "dob": dob, "access_code": code}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class StateLogicTests(unittest.TestCase):
    def test_correct_credentials_pass(self):
        state = _State(rate_limit_enabled=True, lockout_threshold=5, lockout_window_seconds=60)
        status, payload = state.check(DEMO_USER_ID, DEMO_DOB, state.access_code)
        self.assertEqual(status, 200)

    def test_wrong_code_fails(self):
        state = _State(rate_limit_enabled=True, lockout_threshold=5, lockout_window_seconds=60)
        wrong = "000" if state.access_code != "000" else "001"
        status, _ = state.check(DEMO_USER_ID, DEMO_DOB, wrong)
        self.assertEqual(status, 401)

    def test_lockout_after_threshold(self):
        state = _State(rate_limit_enabled=True, lockout_threshold=3, lockout_window_seconds=60)
        wrong = "000" if state.access_code != "000" else "001"
        statuses = [state.check(DEMO_USER_ID, DEMO_DOB, wrong)[0] for _ in range(3)]
        self.assertEqual(statuses, [401, 401, 401])
        locked_status, _ = state.check(DEMO_USER_ID, DEMO_DOB, wrong)
        self.assertEqual(locked_status, 429)

    def test_no_lockout_when_rate_limit_disabled(self):
        state = _State(rate_limit_enabled=False, lockout_threshold=3, lockout_window_seconds=60)
        wrong = "000" if state.access_code != "000" else "001"
        for _ in range(10):
            status, _ = state.check(DEMO_USER_ID, DEMO_DOB, wrong)
            self.assertEqual(status, 401)


class HttpEndToEndTests(unittest.TestCase):
    def _start_server(self, rate_limit_enabled, lockout_threshold=3, lockout_window_seconds=60):
        state = _State(rate_limit_enabled, lockout_threshold, lockout_window_seconds)
        server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        # addCleanup runs LIFO: add join first so shutdown/close (added
        # after) run first, unblocking serve_forever before join waits on it.
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_address[1]
        return state, f"http://127.0.0.1:{port}/instant-access"

    def test_success_over_http(self):
        state, url = self._start_server(rate_limit_enabled=True)
        status, payload = _post(url, DEMO_USER_ID, DEMO_DOB, state.access_code)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_lockout_over_http(self):
        state, url = self._start_server(rate_limit_enabled=True, lockout_threshold=2, lockout_window_seconds=60)
        wrong = "000" if state.access_code != "000" else "001"
        statuses = [_post(url, DEMO_USER_ID, DEMO_DOB, wrong)[0] for _ in range(3)]
        self.assertEqual(statuses, [401, 401, 429])


class LoopbackGuardTests(unittest.TestCase):
    def test_allows_loopback_hosts(self):
        _require_loopback("127.0.0.1")
        _require_loopback("localhost")

    def test_refuses_non_loopback_host(self):
        with self.assertRaises(SystemExit):
            _require_loopback("example.com")


if __name__ == "__main__":
    unittest.main()
