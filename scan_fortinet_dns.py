#!/usr/bin/env python3
"""Fast Fortinet v7.6 detection using DNS + HTTP fingerprinting for .co.il sites.

DNS-first approach: resolve domains quickly, then fingerprint live hosts.

Usage:
    python3 scan_fortinet_dns.py --file israeli_websites_coil_only.txt
"""

import re
import sys
import json
import argparse
import socket
import concurrent.futures
from collections import defaultdict

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("ERROR: requests library required. Install with: pip install requests")
    sys.exit(1)

# Version patterns to detect
VERSION_PATTERNS = {
    "7.6": [
        r"[Vv]ersion\s*[:\s]*7\.6",
        r"FortiOS\s+7\.6",
        r"v7\.6",
        r"7\.6\.\d+",
    ],
    "7.x": [
        r"[Vv]ersion\s*[:\s]*7\.\d",
        r"FortiOS\s+7\.\d",
    ]
}

# Fortinet v7.6 fingerprint indicators
FORTINET_INDICATORS = {
    "headers": {
        "X-Fortinet-FortiGate": r".*",
        "Server": r"(?:FortiGate|FortiWeb|Fortinet)",
    },
    "cookies": [
        "FORTITOKEN",
        "FORTIGATEAUTH",
        "FORTILAST",
    ],
    "html_patterns": [
        r"Fortinet",
        r"FortiGate",
        r"FortiWeb",
        r"fortinet\.com",
    ]
}


def resolve_domain(domain):
    """Fast DNS resolution."""
    try:
        ip = socket.gethostbyname(domain)
        return {"domain": domain, "ip": ip, "reachable": True}
    except (socket.gaierror, socket.timeout):
        return {"domain": domain, "ip": None, "reachable": False, "error": "DNS failed"}


def detect_version(html, headers):
    """Detect Fortinet version from response."""
    combined = html + " ".join(f"{k}:{v}" for k, v in headers.items())

    for version, patterns in VERSION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return version
    return None


def fingerprint_http(domain, timeout=5):
    """HTTP fingerprinting for Fortinet indicators."""
    result = {
        "domain": domain,
        "url": f"https://{domain}",
        "status": None,
        "indicators": [],
        "version": None,
        "confidence": 0,
    }

    try:
        session = requests.Session()
        retries = Retry(total=1, backoff_factor=0.3)
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        resp = session.get(f"https://{domain}", timeout=timeout, verify=False, allow_redirects=False)
        result["status"] = resp.status_code

        confidence = 0

        # Check headers
        for header_name, pattern in FORTINET_INDICATORS["headers"].items():
            header_val = resp.headers.get(header_name, "")
            if header_val and re.search(pattern, header_val, re.IGNORECASE):
                result["indicators"].append(f"Header: {header_name}")
                confidence += 40

        # Check cookies
        for cookie_name in FORTINET_INDICATORS["cookies"]:
            if cookie_name in resp.cookies:
                result["indicators"].append(f"Cookie: {cookie_name}")
                confidence += 30

        # Check HTML
        for pattern in FORTINET_INDICATORS["html_patterns"]:
            if re.search(pattern, resp.text, re.IGNORECASE):
                result["indicators"].append(f"HTML: {pattern[:30]}")
                confidence += 25

        # Detect version
        version = detect_version(resp.text, resp.headers)
        if version:
            result["version"] = version
            if version == "7.6":
                confidence += 30
            elif version == "7.x":
                confidence += 15

        result["confidence"] = min(confidence, 100)

    except requests.exceptions.Timeout:
        result["error"] = "HTTP timeout"
    except requests.exceptions.ConnectionError:
        result["error"] = "Connection error"
    except requests.exceptions.RequestException as e:
        result["error"] = str(e)[:50]

    return result


def main():
    parser = argparse.ArgumentParser(description="Fast Fortinet v8 detection using DNS + HTTP")
    parser.add_argument("--file", required=True, help="File with .co.il domains (one per line)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--timeout", type=int, default=3, help="HTTP timeout (seconds)")
    parser.add_argument("--workers", type=int, default=10, help="Concurrent workers")

    args = parser.parse_args()

    try:
        with open(args.file) as f:
            domains = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Phase 1: DNS resolution for {len(domains)} domains...", file=sys.stderr)

    # Phase 1: DNS resolution
    live_domains = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        dns_results = list(executor.map(resolve_domain, domains))

    live_domains = [r for r in dns_results if r["reachable"]]
    print(f"[*] {len(live_domains)}/{len(domains)} domains resolved live", file=sys.stderr)

    # Phase 2: HTTP fingerprinting
    print(f"[*] Phase 2: HTTP fingerprinting ({args.workers} workers)...", file=sys.stderr)

    fortinet_hits = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for i, result in enumerate(executor.map(lambda d: fingerprint_http(d["domain"], args.timeout), live_domains), 1):
            if i % 50 == 0:
                print(f"[*] [{i}/{len(live_domains)}] Scanned...", file=sys.stderr)

            if result["indicators"] or (result.get("confidence", 0) > 0):
                fortinet_hits.append(result)

    # Results
    print("\n" + "=" * 80, file=sys.stderr)
    print("RESULTS", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(f"Total domains: {len(domains)}", file=sys.stderr)
    print(f"DNS live: {len(live_domains)}", file=sys.stderr)
    print(f"Fortinet detected: {len(fortinet_hits)}", file=sys.stderr)

    if args.json:
        print(json.dumps(fortinet_hits, indent=2))
    else:
        if fortinet_hits:
            print("\nFORTINET DETECTED:", file=sys.stderr)
            print("-" * 80, file=sys.stderr)
            for r in sorted(fortinet_hits, key=lambda x: x.get("confidence", 0), reverse=True):
                print(f"\n{r['domain']}")
                print(f"  Status: {r['status']}")
                print(f"  Confidence: {r['confidence']}%")
                if r["indicators"]:
                    for ind in r["indicators"]:
                        print(f"  - {ind}")
        else:
            print("\nNo Fortinet indicators detected", file=sys.stderr)


if __name__ == "__main__":
    main()
