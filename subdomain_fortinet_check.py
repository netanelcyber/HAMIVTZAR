#!/usr/bin/env python3
"""Subdomain enumeration + Fortinet detection.

Finds subdomains, then checks each for Fortinet v7.6/v8 indicators.

Usage:
    python3 subdomain_fortinet_check.py --domain ynet.co.il
    python3 subdomain_fortinet_check.py --file domains.txt
"""

import sys
import socket
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

# Common subdomains
COMMON_SUBDOMAINS = [
    "www", "mail", "smtp", "admin", "api", "dev", "test", "staging",
    "vpn", "gateway", "firewall", "waf", "db", "cache", "cdn",
    "jenkins", "gitlab", "dashboard", "monitoring", "auth", "passport",
    "qa", "prod", "production", "backup", "logs", "metrics", "chat",
    "webhook", "build", "deploy", "app", "application", "service",
]

# Fortinet indicators
FORTINET_PATTERNS = {
    "headers": {
        "X-Fortinet-FortiGate": r".*",
        "Server": r"(?:FortiGate|FortiWeb|Fortinet)",
    },
    "html": [
        r"Fortinet",
        r"FortiGate",
        r"FortiWeb",
    ]
}

VERSION_PATTERNS = {
    "7.6": [r"7\.6", r"FortiOS\s+7\.6"],
    "7.x": [r"FortiOS\s+7\.\d"],
    "8.x": [r"8\.\d", r"FortiOS\s+8"],
}


def resolve_subdomain(subdomain, domain):
    """Quick DNS resolution."""
    try:
        ip = socket.gethostbyname(f"{subdomain}.{domain}")
        return {"subdomain": subdomain, "domain": domain, "ip": ip}
    except:
        return None


def check_fortinet(full_domain, timeout=3):
    """Check if subdomain has Fortinet indicators."""
    result = {
        "domain": full_domain,
        "status": None,
        "fortinet": False,
        "version": None,
        "indicators": [],
    }

    try:
        session = requests.Session()
        retries = Retry(total=1, backoff_factor=0.2)
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        resp = session.get(f"https://{full_domain}", timeout=timeout, verify=False, allow_redirects=False)
        result["status"] = resp.status_code

        # Check headers
        for header, pattern in FORTINET_PATTERNS["headers"].items():
            if header in resp.headers and re.search(pattern, resp.headers[header], re.IGNORECASE):
                result["fortinet"] = True
                result["indicators"].append(f"Header: {header}")

        # Check HTML
        for pattern in FORTINET_PATTERNS["html"]:
            if re.search(pattern, resp.text, re.IGNORECASE):
                result["fortinet"] = True
                result["indicators"].append(f"HTML: {pattern[:20]}")

        # Version detection
        combined = resp.text + " ".join(resp.headers.values())
        for version, patterns in VERSION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    result["version"] = version
                    break

    except requests.exceptions.Timeout:
        result["error"] = "timeout"
    except requests.exceptions.ConnectionError:
        result["error"] = "connection_error"
    except Exception as e:
        result["error"] = str(e)[:30]

    return result


def main():
    parser = argparse.ArgumentParser(description="Subdomain enumeration + Fortinet detection")
    parser.add_argument("--domain", help="Single domain")
    parser.add_argument("--file", help="File with domains")
    parser.add_argument("--workers", type=int, default=30, help="Concurrent workers")

    args = parser.parse_args()

    domains = []
    if args.domain:
        domains = [args.domain]
    elif args.file:
        with open(args.file) as f:
            domains = [line.strip() for line in f if line.strip()]
    else:
        parser.print_help()
        sys.exit(1)

    all_subdomains = []
    fortinet_hits = []

    # Phase 1: Enumerate subdomains
    print(f"[*] Phase 1: Enumerating subdomains for {len(domains)} domain(s)...", file=sys.stderr)

    for domain in domains:
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            futures = [
                executor.submit(resolve_subdomain, sub, domain)
                for sub in COMMON_SUBDOMAINS
            ]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    all_subdomains.append(f"{result['subdomain']}.{result['domain']}")

    print(f"[*] Found {len(all_subdomains)} live subdomains", file=sys.stderr)

    # Phase 2: Check for Fortinet
    print(f"[*] Phase 2: Checking {len(all_subdomains)} subdomains for Fortinet...", file=sys.stderr)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for i, result in enumerate(executor.map(check_fortinet, all_subdomains), 1):
            if result["fortinet"]:
                fortinet_hits.append(result)

            if i % 20 == 0:
                print(f"[*] [{i}/{len(all_subdomains)}] checked...", file=sys.stderr)

    # Results
    print("\n" + "=" * 80, file=sys.stderr)
    print("RESULTS", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print(f"Total subdomains: {len(all_subdomains)}", file=sys.stderr)
    print(f"Fortinet detected: {len(fortinet_hits)}", file=sys.stderr)

    if fortinet_hits:
        print("\n🔴 FORTINET DETECTED:", file=sys.stderr)
        print("-" * 80, file=sys.stderr)
        for hit in sorted(fortinet_hits, key=lambda x: x["version"] or ""):
            print(f"\n{hit['domain']}")
            print(f"  Status: {hit['status']}")
            if hit['version']:
                print(f"  Version: {hit['version']}")
            for ind in hit['indicators']:
                print(f"  - {ind}")
    else:
        print("\n✅ No Fortinet detected", file=sys.stderr)

    # Print subdomain list
    print("\n" + "=" * 80, file=sys.stderr)
    print("ALL SUBDOMAINS FOUND:", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    for sub in sorted(all_subdomains):
        print(sub)


if __name__ == "__main__":
    main()
