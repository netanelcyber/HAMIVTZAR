"""Rehearse testing AC-6/AC-7 (rate limiting / lockout on a patient
self-service login) against the local mock server in this package --
never against a real system.

This script hard-refuses to target anything other than 127.0.0.1/localhost.
That is not configurable, on purpose: it is a rehearsal client for
``mock_patient_portal.py``, not a general-purpose credential-guessing tool.

Usage (in one terminal):
    python -m pacs_iso27799_audit.lab.mock_patient_portal --no-rate-limit

Usage (in another terminal) -- unprotected run, should eventually "succeed":
    python -m pacs_iso27799_audit.lab.rehearse_lockout_check

Then stop the server, restart it WITH rate limiting (the default), and run
this again to see it get locked out instead:
    python -m pacs_iso27799_audit.lab.mock_patient_portal
    python -m pacs_iso27799_audit.lab.rehearse_lockout_check
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

from .mock_patient_portal import CODE_SPACE, DEMO_DOB, FIELD_CODE, FIELD_DOB

_ALLOWED_HOSTS = {"127.0.0.1", "localhost"}


def _require_loopback(host: str) -> None:
    if host not in _ALLOWED_HOSTS:
        raise SystemExit(
            f"Refusing to target {host!r}. This rehearsal client only ever talks to "
            f"{sorted(_ALLOWED_HOSTS)} -- point it at your own local "
            f"mock_patient_portal.py instance, not a real host."
        )


def _attempt(url: str, dob: str, code: str) -> tuple:
    body = urlencode({FIELD_DOB: dob, FIELD_CODE: code}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1", choices=sorted(_ALLOWED_HOSTS))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--dob", default=DEMO_DOB)
    parser.add_argument("--max-attempts", type=int, default=CODE_SPACE)
    args = parser.parse_args(argv)

    _require_loopback(args.host)
    url = f"http://{args.host}:{args.port}/instant-access"

    start = time.monotonic()
    for attempt in range(1, args.max_attempts + 1):
        code = f"{attempt - 1:03d}"
        try:
            status, payload = _attempt(url, args.dob, code)
        except (urllib.error.URLError, ConnectionError) as e:
            print(f"Could not reach {url}: {e}. Is mock_patient_portal.py running?")
            return 1

        if status == 200:
            elapsed = time.monotonic() - start
            print(f"Guessed correctly after {attempt} attempt(s) in {elapsed:.1f}s: {payload}")
            print("This is the failure mode AC-6/AC-7 exist to prevent -- rerun the "
                  "server WITHOUT --no-rate-limit to see lockout stop this.")
            return 0

        if status == 429:
            elapsed = time.monotonic() - start
            print(f"Locked out after {attempt} attempt(s) in {elapsed:.1f}s: {payload}")
            print("Rate limiting/lockout is doing its job -- brute force did not "
                  "reach the correct code in the allotted attempts.")
            return 0

    print(f"Exhausted {args.max_attempts} attempts without success or lockout.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
