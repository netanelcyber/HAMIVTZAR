#!/usr/bin/env python3
"""Scan Israeli websites for Fortinet v8 detection.

Usage:
    python3 scan_fortinet_v8.py <url1> <url2> ...
    python3 scan_fortinet_v8.py --file urls.txt
"""

import re
import sys
import json
import argparse
from urllib.parse import urljoin
from collections import defaultdict

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("ERROR: requests library required. Install with: pip install requests")
    sys.exit(1)


# Fortinet v8 fingerprint indicators
FORTINET_INDICATORS = {
    "headers": {
        "X-Fortinet-FortiGate": r".*",
        "Server": r"(?:FortiGate|FortiWeb|Fortinet)",
        "X-Content-Type-Options": r"nosniff",  # Common in Fortinet
    },
    "cookies": {
        "FORTITOKEN": None,
        "FORTIGATEAUTH": None,
        "FORTILAST": None,
    },
    "paths": [
        "/loginpage.html",
        "/remote/login",
        "/admin/",
        "/.well-known/",
    ],
    "html_patterns": [
        r"Fortinet",
        r"FortiGate",
        r"FortiWeb",
        r"fortinet\.com",
        r"Powered by.*Fortinet",
    ]
}

VERSION_PATTERNS = {
    "v8": [
        r"[Vv]ersion\s*[:\s]*8\.",
        r"v8\.",
        r"8\.\d+",
    ],
    "v7": [
        r"[Vv]ersion\s*[:\s]*7\.",
        r"v7\.",
        r"7\.\d+",
    ],
}


def session_with_retries():
    """Create requests session with retry logic."""
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def scan_url(url, session, timeout=10):
    """Scan a single URL for Fortinet indicators."""
    result = {
        "url": url,
        "reachable": False,
        "status": None,
        "indicators": [],
        "version": None,
        "confidence": 0,
    }

    try:
        # Ensure URL has scheme
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            result["url"] = url

        resp = session.get(url, timeout=timeout, verify=True, allow_redirects=True)
        result["reachable"] = True
        result["status"] = resp.status_code

        indicators = []
        confidence_score = 0

        # Check headers
        for header_name, pattern in FORTINET_INDICATORS["headers"].items():
            header_val = resp.headers.get(header_name, "")
            if header_val and re.search(pattern, header_val, re.IGNORECASE):
                indicators.append(f"Header: {header_name}={header_val[:60]}")
                confidence_score += 30

        # Check cookies
        for cookie_name in FORTINET_INDICATORS["cookies"]:
            if cookie_name in resp.cookies:
                indicators.append(f"Cookie: {cookie_name}")
                confidence_score += 20

        # Check HTML body patterns
        html_lower = resp.text.lower()
        for pattern in FORTINET_INDICATORS["html_patterns"]:
            if re.search(pattern, resp.text, re.IGNORECASE):
                indicators.append(f"HTML: {pattern[:40]}")
                confidence_score += 25

        # Try to detect version
        version = detect_version(resp.text, resp.headers)
        if version:
            result["version"] = version
            if version == "v8":
                confidence_score += 20

        result["indicators"] = indicators
        result["confidence"] = min(confidence_score, 100)

    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
    except requests.exceptions.ConnectionError:
        result["error"] = "Connection error"
    except requests.exceptions.RequestException as e:
        result["error"] = str(e)[:100]

    return result


def detect_version(html, headers):
    """Try to detect Fortinet version from response."""
    combined = html + " ".join(f"{k}:{v}" for k, v in headers.items())

    for version, patterns in VERSION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return version
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Scan Israeli websites for Fortinet v8 indicators"
    )
    parser.add_argument("urls", nargs="*", help="URLs to scan")
    parser.add_argument("--file", help="File containing URLs (one per line)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout (seconds)")

    args = parser.parse_args()

    urls = list(args.urls)
    if args.file:
        try:
            with open(args.file) as f:
                urls.extend(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            print(f"ERROR: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)

    if not urls:
        print("ERROR: No URLs provided", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    session = session_with_retries()
    results = []

    print(f"[*] Scanning {len(urls)} URL(s) for Fortinet v8...", file=sys.stderr)

    for i, url in enumerate(urls, 1):
        url = url.strip()
        if not url:
            continue

        print(f"[*] [{i}/{len(urls)}] Scanning {url}...", file=sys.stderr)
        result = scan_url(url, session, timeout=args.timeout)
        results.append(result)

    # Summary
    fortinet_detected = [r for r in results if r["indicators"]]
    fortinet_v8 = [r for r in results if r["version"] == "v8"]
    high_confidence = [r for r in results if r["confidence"] >= 50]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"Total scanned: {len(results)}")
        print(f"Reachable: {sum(1 for r in results if r['reachable'])}")
        print(f"Fortinet detected: {len(fortinet_detected)}")
        print(f"  - High confidence (≥50%): {len(high_confidence)}")
        print(f"  - Version 8: {len(fortinet_v8)}")

        if high_confidence:
            print("\n" + "-" * 80)
            print("HIGH CONFIDENCE HITS (Fortinet Detected):")
            print("-" * 80)
            for r in high_confidence:
                print(f"\n{r['url']}")
                print(f"  Status: {r['status']}")
                print(f"  Confidence: {r['confidence']}%")
                if r["version"]:
                    print(f"  Version: {r['version']}")
                if r["indicators"]:
                    print(f"  Indicators:")
                    for ind in r["indicators"]:
                        print(f"    - {ind}")

        if fortinet_v8:
            print("\n" + "-" * 80)
            print("FORTINET V8 CONFIRMED:")
            print("-" * 80)
            for r in fortinet_v8:
                print(f"  {r['url']}")


if __name__ == "__main__":
    main()
