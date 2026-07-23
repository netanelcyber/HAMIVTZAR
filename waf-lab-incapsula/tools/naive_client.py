#!/usr/bin/env python3
"""
Baseline: a default `requests` call against the lab WAF, with no evasion at
all. Expected to be blocked immediately (default User-Agent contains
"python-requests", which is on the WAF's blocked-signature list). Run this
first so the later bypass scripts have something to contrast with.

    python3 naive_client.py http://localhost:8080/
"""
import sys

import requests


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/"
    resp = requests.get(url, timeout=5)
    print(f"GET {url} -> {resp.status_code}")
    print(resp.text[:500])


if __name__ == "__main__":
    main()
