#!/usr/bin/env python3
"""Fortinet v7.4+ detection (7.4, 7.5, 7.6, 8.x) for 657 Israeli domains.

Scans using DNS + HTTP fingerprinting for Fortinet indicators.

Usage:
    python3 scan_fortinet_7_4_plus.py --file israeli_websites_coil_only.txt
"""

import socket
import sys
import argparse
import re
import concurrent.futures
from collections import defaultdict

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("ERROR: requests library required", file=sys.stderr)
    sys.exit(1)

# Fortinet v7.4+ indicators
FORTINET_INDICATORS = {
    "headers": {
        "X-Fortinet-FortiGate": r".*",
        "Server": r"(?:FortiGate|FortiWeb|Fortinet)",
        "X-Powered-By": r"Fortinet",
    },
    "cookies": [
        "FORTITOKEN",
        "FORTIGATEAUTH",
        "FORTILAST",
        "FORTICLIENT",
    ],
    "html_patterns": [
        r"Fortinet",
        r"FortiGate",
        r"FortiWeb",
        r"FortiOS",
        r"fortinet\.com",
    ]
}

# Version detection patterns for 7.4+
VERSION_PATTERNS = {
    "7.4": [
        r"(?i)7\.4(?:\.\d+)?",
        r"(?i)FortiOS\s+7\.4",
        r"(?i)FortiGate.*7\.4",
    ],
    "7.5": [
        r"(?i)7\.5(?:\.\d+)?",
        r"(?i)FortiOS\s+7\.5",
        r"(?i)FortiGate.*7\.5",
    ],
    "7.6": [
        r"(?i)7\.6(?:\.\d+)?",
        r"(?i)FortiOS\s+7\.6",
        r"(?i)FortiGate.*7\.6",
    ],
    "7.x": [
        r"(?i)7\.\d(?:\.\d+)?",
        r"(?i)FortiOS\s+7\.\d",
    ],
    "8.x": [
        r"(?i)8\.\d(?:\.\d+)?",
        r"(?i)FortiOS\s+8\.\d",
        r"(?i)FortiGate.*8\.\d",
    ],
}


def resolve_domain(domain):
    """Fast DNS resolution."""
    try:
        ip = socket.gethostbyname(domain)
        return ip
    except socket.gaierror:
        return None


def detect_version(text, headers):
    """Detect Fortinet version from response."""
    combined = text + " ".join(f"{k}:{v}" for k, v in headers.items())

    detected = []
    for version, patterns in VERSION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, combined):
                detected.append(version)
                break

    return detected[0] if detected else None


def check_fortinet(domain, ip, timeout=3):
    """Check domain for Fortinet indicators."""
    result = {
        "domain": domain,
        "ip": ip,
        "fortinet": False,
        "version": None,
        "confidence": 0,
        "indicators": [],
    }

    try:
        session = requests.Session()
        retries = Retry(total=1, backoff_factor=0.2)
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        resp = session.get(f"https://{domain}", timeout=timeout, verify=False, allow_redirects=False)

        confidence = 0

        # Check headers
        for header_name, pattern in FORTINET_INDICATORS["headers"].items():
            if header_name in resp.headers:
                header_val = resp.headers[header_name]
                if re.search(pattern, header_val, re.IGNORECASE):
                    result["fortinet"] = True
                    result["indicators"].append(f"Header: {header_name}")
                    confidence += 40

        # Check cookies
        for cookie_name in FORTINET_INDICATORS["cookies"]:
            if cookie_name in resp.cookies:
                result["fortinet"] = True
                result["indicators"].append(f"Cookie: {cookie_name}")
                confidence += 30

        # Check HTML
        for pattern in FORTINET_INDICATORS["html_patterns"]:
            if re.search(pattern, resp.text, re.IGNORECASE):
                result["fortinet"] = True
                result["indicators"].append(f"HTML: {pattern[:25]}")
                confidence += 25

        # Detect version
        if result["fortinet"]:
            version = detect_version(resp.text, resp.headers)
            if version:
                result["version"] = version
                if version.startswith("7.4"):
                    confidence += 40
                elif version.startswith("7"):
                    confidence += 30
                elif version.startswith("8"):
                    confidence += 35

        result["confidence"] = min(confidence, 100)

    except Exception as e:
        result["error"] = str(e)[:50]

    return result


def main():
    parser = argparse.ArgumentParser(description="Scan for Fortinet v7.4+ (7.4, 7.5, 7.6, 8.x)")
    parser.add_argument("--file", required=True, help="File with domains")
    parser.add_argument("--workers", type=int, default=30, help="Concurrent workers")

    args = parser.parse_args()

    # Load domains
    try:
        with open(args.file) as f:
            domains = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Scanning {len(domains)} domains for Fortinet v7.4+ ...", file=sys.stderr)

    # Phase 1: DNS resolution
    live_domains = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
        for domain, ip in zip(domains, executor.map(resolve_domain, domains)):
            if ip:
                live_domains[domain] = ip

    print(f"[*] {len(live_domains)}/{len(domains)} domains live", file=sys.stderr)

    # Phase 2: Fortinet detection
    results = []
    fortinet_hits = defaultdict(list)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for i, result in enumerate(executor.map(
            lambda d: check_fortinet(d, live_domains[d]),
            live_domains.keys()
        ), 1):
            results.append(result)

            if result["fortinet"]:
                version = result["version"] or "unknown"
                fortinet_hits[version].append(result)

            if i % 50 == 0:
                print(f"[*] [{i}/{len(live_domains)}] checked...", file=sys.stderr)

    # Results
    print("\n" + "=" * 80, file=sys.stderr)
    print("FORTINET v7.4+ DETECTION RESULTS", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(f"Total domains: {len(domains)}", file=sys.stderr)
    print(f"DNS live: {len(live_domains)}", file=sys.stderr)
    print(f"\nFortinet v7.4+ Found:", file=sys.stderr)
    print(f"  Total: {sum(len(v) for v in fortinet_hits.values())}", file=sys.stderr)

    if fortinet_hits:
        for version in sorted(fortinet_hits.keys()):
            print(f"  {version}: {len(fortinet_hits[version])}", file=sys.stderr)

        print("\n" + "=" * 80, file=sys.stderr)
        print("DETAILED FINDINGS", file=sys.stderr)
        print("=" * 80, file=sys.stderr)

        for version in sorted(fortinet_hits.keys(), reverse=True):
            print(f"\n🔴 Fortinet {version} ({len(fortinet_hits[version])} domains):", file=sys.stderr)
            for hit in sorted(fortinet_hits[version], key=lambda x: x["confidence"], reverse=True):
                print(f"\n  {hit['domain']} ({hit['ip']})", file=sys.stderr)
                print(f"    Confidence: {hit['confidence']}%", file=sys.stderr)
                if hit["indicators"]:
                    for ind in hit["indicators"]:
                        print(f"    - {ind}", file=sys.stderr)
    else:
        print(f"  Total: 0", file=sys.stderr)
        print("\n✅ No Fortinet v7.4+ detected", file=sys.stderr)

    # CSV output
    print("\n" + "=" * 80, file=sys.stderr)
    print("CSV EXPORT:", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("domain,ip,fortinet,version,confidence")
    for r in sorted(results, key=lambda x: x["confidence"], reverse=True):
        fortinet_str = "yes" if r["fortinet"] else "no"
        version_str = r.get("version", "")
        conf_str = str(r["confidence"]) if r["fortinet"] else ""
        print(f'{r["domain"]},{r["ip"]},{fortinet_str},{version_str},{conf_str}')


if __name__ == "__main__":
    main()
