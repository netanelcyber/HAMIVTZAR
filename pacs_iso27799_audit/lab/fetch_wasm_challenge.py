"""Fetch the WASM reverse-engineering challenge module from the local mock
server and save it to a file -- never against a real system.

Hard-refuses any target other than 127.0.0.1/localhost, same as the other
rehearsal scripts (reuses rehearse_lockout_check.py's guard directly). This
is just download plumbing; it does not analyze or solve anything -- see
inspect_wasm.py for the disassembler, and lab/README.md for the exercise.

Usage:
    python -m pacs_iso27799_audit.lab.mock_patient_portal
    python -m pacs_iso27799_audit.lab.fetch_wasm_challenge --output access-check.wasm
    python -m pacs_iso27799_audit.lab.inspect_wasm access-check.wasm
"""

from __future__ import annotations

import argparse
import urllib.request

from .rehearse_lockout_check import _ALLOWED_HOSTS, _require_loopback


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1", choices=sorted(_ALLOWED_HOSTS))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--output", default="access-check.wasm")
    args = parser.parse_args(argv)

    _require_loopback(args.host)
    url = f"http://{args.host}:{args.port}/static/access-check.wasm"

    with urllib.request.urlopen(url, timeout=5) as resp:
        data = resp.read()

    with open(args.output, "wb") as f:
        f.write(data)

    print(f"Saved {len(data)} bytes to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
