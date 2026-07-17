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
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pacs_iso27799_audit.lab.mock_patient_portal import (
    DEMO_DOB,
    FIELD_CODE,
    FIELD_DOB,
    FIELD_EVENTVALIDATION,
    FIELD_VIEWSTATE,
    _State,
    _make_handler,
)
from pacs_iso27799_audit.lab.rehearse_lockout_check import _require_loopback


def _get_token(base_url):
    with urllib.request.urlopen(f"{base_url}/login", timeout=5) as resp:
        return json.loads(resp.read())


def _post(base_url, dob, code, token=None):
    form = {FIELD_DOB: dob, FIELD_CODE: code}
    form.update(token or {})
    body = urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/instant-access", data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class StateLogicTests(unittest.TestCase):
    def test_correct_credentials_pass(self):
        state = _State(rate_limit_enabled=True, lockout_threshold=5, lockout_window_seconds=60)
        status, payload = state.check(DEMO_DOB, state.access_code)
        self.assertEqual(status, 200)

    def test_wrong_code_fails(self):
        state = _State(rate_limit_enabled=True, lockout_threshold=5, lockout_window_seconds=60)
        wrong = "000" if state.access_code != "000" else "001"
        status, _ = state.check(DEMO_DOB, wrong)
        self.assertEqual(status, 401)

    def test_lockout_after_threshold(self):
        state = _State(rate_limit_enabled=True, lockout_threshold=3, lockout_window_seconds=60)
        wrong = "000" if state.access_code != "000" else "001"
        statuses = [state.check(DEMO_DOB, wrong)[0] for _ in range(3)]
        self.assertEqual(statuses, [401, 401, 401])
        locked_status, _ = state.check(DEMO_DOB, wrong)
        self.assertEqual(locked_status, 429)

    def test_no_lockout_when_rate_limit_disabled(self):
        state = _State(rate_limit_enabled=False, lockout_threshold=3, lockout_window_seconds=60)
        wrong = "000" if state.access_code != "000" else "001"
        for _ in range(10):
            status, _ = state.check(DEMO_DOB, wrong)
            self.assertEqual(status, 401)


class TokenLogicTests(unittest.TestCase):
    def test_freshly_issued_token_is_consumable_once(self):
        state = _State(rate_limit_enabled=True, lockout_threshold=5, lockout_window_seconds=60)
        viewstate, eventvalidation = state.issue_token()
        self.assertTrue(state.consume_token(viewstate, eventvalidation))
        self.assertFalse(state.consume_token(viewstate, eventvalidation))  # single-use

    def test_tampered_eventvalidation_is_rejected(self):
        state = _State(rate_limit_enabled=True, lockout_threshold=5, lockout_window_seconds=60)
        viewstate, _ = state.issue_token()
        self.assertFalse(state.consume_token(viewstate, "not-the-real-mac"))

    def test_unknown_viewstate_is_rejected(self):
        state = _State(rate_limit_enabled=True, lockout_threshold=5, lockout_window_seconds=60)
        self.assertFalse(state.consume_token("never-issued", "whatever"))


class HttpEndToEndTests(unittest.TestCase):
    def _start_server(self, rate_limit_enabled, lockout_threshold=3, lockout_window_seconds=60,
                       postback_tokens_enabled=True):
        state = _State(rate_limit_enabled, lockout_threshold, lockout_window_seconds, postback_tokens_enabled)
        server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        # addCleanup runs LIFO: add join first so shutdown/close (added
        # after) run first, unblocking serve_forever before join waits on it.
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_address[1]
        return state, f"http://127.0.0.1:{port}"

    def test_success_over_http_with_fresh_token(self):
        state, url = self._start_server(rate_limit_enabled=True)
        token = _get_token(url)
        status, payload = _post(url, DEMO_DOB, state.access_code, token)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_post_without_token_is_rejected_when_enabled(self):
        state, url = self._start_server(rate_limit_enabled=True, postback_tokens_enabled=True)
        status, payload = _post(url, DEMO_DOB, state.access_code)  # no token
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid_or_expired_postback_token")

    def test_post_without_token_succeeds_when_disabled(self):
        state, url = self._start_server(rate_limit_enabled=True, postback_tokens_enabled=False)
        status, payload = _post(url, DEMO_DOB, state.access_code)  # no token needed
        self.assertEqual(status, 200)

    def test_reusing_a_token_is_rejected(self):
        state, url = self._start_server(rate_limit_enabled=True)
        token = _get_token(url)
        wrong = "000" if state.access_code != "000" else "001"
        first_status, _ = _post(url, DEMO_DOB, wrong, token)
        second_status, second_payload = _post(url, DEMO_DOB, wrong, token)
        self.assertEqual(first_status, 401)  # wrong code, but token accepted
        self.assertEqual(second_status, 400)  # token already used
        self.assertEqual(second_payload["error"], "invalid_or_expired_postback_token")

    def test_lockout_over_http(self):
        state, url = self._start_server(rate_limit_enabled=True, lockout_threshold=2, lockout_window_seconds=60)
        wrong = "000" if state.access_code != "000" else "001"
        statuses = [_post(url, DEMO_DOB, wrong, _get_token(url))[0] for _ in range(3)]
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
