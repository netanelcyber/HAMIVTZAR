"""Rehearse endpoint discovery / fingerprinting against the local mock
server in this package -- never against a real system.

Hard-refuses any target other than 127.0.0.1/localhost, same as
rehearse_lockout_check.py -- reuses its guard directly rather than
duplicating it.

Probes a small built-in candidate path list. For each path it tries GET
first; if that 404s, it retries with POST (empty body) -- since a real
recon pass doesn't know a route's method in advance either. A small delay
between requests mirrors good rate-limiting practice during recon (see
pentest-milatova/scope.md's "rate-limit all requests" rule) even though
there is no real server here to be polite to.

This intentionally does NOT print the endpoint list from
mock_patient_portal.py's docstring -- read the output here, then compare
against that file afterward if you want to check your findings.

Usage:
    python -m pacs_iso27799_audit.lab.mock_patient_portal
    python -m pacs_iso27799_audit.lab.rehearse_endpoint_recon
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request

from .rehearse_lockout_check import _ALLOWED_HOSTS, _require_loopback

# A handful of real hits mixed with plausible-but-absent decoys, so "found
# it" isn't a given for every entry -- same spirit as a real recon wordlist.
CANDIDATE_PATHS = [
    "/login",
    "/instant-access",
    "/api/patient/exams",
    "/api/patient/profile",
    "/change-password",
    "/logout",
    "/health",
    "/version",
    "/admin/debug",
    "/internal/status",
    "/robots.txt",
    "/backup.zip",
    "/config.json",
    "/api/admin/users",
]

_INTERPRETATION = {
    200: "responded -- likely a real, currently-open endpoint",
    401: "requires auth -- endpoint exists behind a session/token check",
    400: "bad request but not 404 -- endpoint exists, input didn't satisfy it",
    404: "not found",
    405: "method not allowed -- endpoint exists, wrong verb",
}


def _try(url: str, method: str) -> int:
    req = urllib.request.Request(url, method=method, data=b"" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1", choices=sorted(_ALLOWED_HOSTS))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--delay-seconds", type=float, default=0.05)
    args = parser.parse_args(argv)

    _require_loopback(args.host)
    base_url = f"http://{args.host}:{args.port}"

    print(f"Probing {len(CANDIDATE_PATHS)} candidate paths against {base_url} ...")
    print()
    found = 0
    for path in CANDIDATE_PATHS:
        url = f"{base_url}{path}"
        try:
            status = _try(url, "GET")
            method = "GET"
            if status == 404:
                status = _try(url, "POST")
                method = "POST"
        except (urllib.error.URLError, ConnectionError) as e:
            print(f"  {path:24s} -- could not reach server: {e}")
            return 1

        note = _INTERPRETATION.get(status, "unexpected status")
        marker = " " if status == 404 else "*"
        if status != 404:
            found += 1
        print(f"{marker} {path:24s} {method:5s} -> {status}  ({note})")
        time.sleep(args.delay_seconds)

    print()
    print(f"{found}/{len(CANDIDATE_PATHS)} candidate paths resolved to something other than 404.")
    print("Compare against mock_patient_portal.py's docstring to check your findings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
