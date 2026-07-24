#!/usr/bin/env python3
"""
Incapsula Challenge Cracker - end-to-end pipeline

Fetches a target behind Incapsula using previously-extracted cookies. If the
response is an Incapsula challenge/block page (the `<iframe id="main-iframe"
src="...">` wrapper), follows the iframe to the actual sensor/challenge
script and runs the existing obfuscation + anti-detection + RC4 analysis
tools on it in one shot, looking specifically for code that builds the
`visid_incap_*` / `incap_ses_*` cookie values.

This only fetches from the *target itself* - it does not reach out anywhere
else. If your environment cannot reach the target (corporate proxy, sandboxed
container, etc.) this will fail at the first request with a clear network
error; run it from an environment that can actually reach the target.

Usage:
    python3 crack_incapsula_challenge.py <url> <visid_cookie> <incap_ses_cookie>
    python3 crack_incapsula_challenge.py <url> <visid_cookie> <incap_ses_cookie> --save-dir out/
"""

import sys
import re
import json
from pathlib import Path
from argparse import ArgumentParser
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).parent))

from authenticated_requests import AuthenticatedRequests  # noqa: E402
from deobfuscator import JSDeobfuscator  # noqa: E402
from anti_detection_analyzer import AntiDetectionAnalyzer  # noqa: E402
from rc4_decryptor import PayloadAnalyzer  # noqa: E402

IFRAME_SRC_RE = re.compile(r'<iframe[^>]*\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
INCIDENT_ID_RE = re.compile(r"Incapsula incident ID:\s*([\w-]+)", re.IGNORECASE)

# Keywords that point at cookie/token-generation logic specifically, as
# opposed to the generic detection-mechanism keywords anti_detection_analyzer
# already covers.
COOKIE_LOGIC_KEYWORDS = [
    "visid_incap",
    "incap_ses",
    "SWJIYLWA",
    "___utmvc",
    "reese84",
    "nonce",
    "token",
    "compute",
    "digest",
    "fingerprint",
    "document.cookie",
]


def find_iframe_src(html: str) -> str:
    match = IFRAME_SRC_RE.search(html)
    return match.group(1) if match else ""


def find_incident_id(html: str) -> str:
    match = INCIDENT_ID_RE.search(html)
    return match.group(1) if match else ""


def scan_for_cookie_logic(code: str) -> dict:
    """Locate lines mentioning cookie/token-generation keywords, with context."""
    findings = {}
    lines = code.splitlines()
    for keyword in COOKIE_LOGIC_KEYWORDS:
        hits = []
        for i, line in enumerate(lines):
            if keyword.lower() in line.lower():
                snippet = line.strip()[:200]
                hits.append({"line": i + 1, "snippet": snippet})
        if hits:
            findings[keyword] = hits[:10]
    return findings


def run_static_analysis(code: str, label: str) -> dict:
    print("\n" + "=" * 80)
    print(f"STATIC ANALYSIS: {label}")
    print("=" * 80)

    deobf = JSDeobfuscator(code)
    obf_results = deobf.analyze()
    print(f"[*] Size: {len(code):,} bytes")
    print(f"[*] Hex-encoded strings: {obf_results['hex_sequences']}")
    print(f"[*] String arrays: {len(obf_results['string_arrays'])}")
    print(f"[*] Suspicious patterns: {len(obf_results['suspicious_patterns'])}")
    for name, desc in obf_results["suspicious_patterns"]:
        print(f"    - {name}: {desc}")

    detector = AntiDetectionAnalyzer(code)
    detections = detector.analyze()
    print(f"\n[*] Detection mechanisms found: {len(detections)}")
    for name in detections:
        print(f"    - {name}")

    rc4 = PayloadAnalyzer(code)
    rc4_results = rc4.analyze()
    print(f"\n[*] RC4 indicators: {rc4_results['rc4_indicators']}")
    print(f"[*] Base64 payloads: {len(rc4_results['base64_payloads'])}")
    print(f"[*] Possible RC4 keys found in code: {rc4_results['possible_keys']}")

    cookie_logic = scan_for_cookie_logic(code)
    print(f"\n[*] Cookie/token-generation keyword hits:")
    if not cookie_logic:
        print("    (none of the tracked keywords appear - code may be minified/renamed)")
    for keyword, hits in cookie_logic.items():
        print(f"    - '{keyword}': {len(hits)} line(s), e.g. line {hits[0]['line']}: {hits[0]['snippet']}")

    return {
        "label": label,
        "size": len(code),
        "obfuscation": obf_results,
        "detections": detections,
        "rc4": rc4_results,
        "cookie_logic": cookie_logic,
    }


def main():
    parser = ArgumentParser(description="Fetch + crack an Incapsula challenge page end-to-end")
    parser.add_argument("url", help="Target URL (protected by Incapsula)")
    parser.add_argument("visid", help="visid_incap_* cookie value")
    parser.add_argument("incap_ses", help="incap_ses_* cookie value")
    parser.add_argument("--save-dir", default=".", help="Directory to save fetched HTML/JS and report (default: .)")
    parser.add_argument("--no-impersonate", action="store_true", help="Disable curl_cffi Chrome TLS impersonation")
    args = parser.parse_args()

    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("INCAPSULA CHALLENGE CRACKER")
    print("=" * 80)

    auth = AuthenticatedRequests(args.url, args.visid, args.incap_ses, impersonate=not args.no_impersonate)

    # Step 1: fetch the target itself
    result = auth.get("/")
    html = result.get("full_content") or ""

    (save_dir / "response_page.html").write_text(html, encoding="utf-8")

    if result["status"] == 200 and "<iframe" not in html.lower():
        print("\n✓ Got a 200 with no challenge iframe - cookies are accepted, this is real content.")
        print(f"  Saved to {save_dir / 'response_page.html'}")
        run_static_analysis(html, "Target page (real content)")
        return 0

    iframe_src = find_iframe_src(html)
    incident_id = find_incident_id(html)

    if not iframe_src:
        print("\n⚠️ No iframe found in the response and status wasn't a clean 200.")
        print("   This might be a different block format (plain 403 JSON, custom error page, etc).")
        print(f"   Raw response saved to {save_dir / 'response_page.html'} for manual inspection.")
        print(f"\n  Preview: {html[:500]!r}")
        return 1

    print(f"\n[!] This is an Incapsula challenge/block page, not real content.")
    if incident_id:
        print(f"    Incident ID: {incident_id}")
    print(f"    iframe src:  {iframe_src}")

    # Resolve relative src against the target URL
    full_script_url = urljoin(result["url"], iframe_src)
    print(f"    Resolved:    {full_script_url}")

    # Step 2: fetch the actual challenge script through the iframe src,
    # reusing the same authenticated session/cookies.
    parsed = urlparse(full_script_url)
    path_and_query = parsed.path + (("?" + parsed.query) if parsed.query else "")
    script_result = auth.get(path_and_query)
    script_body = script_result.get("full_content") or ""

    (save_dir / "challenge_script.js").write_text(script_body, encoding="utf-8")
    print(f"\n✓ Challenge resource saved to {save_dir / 'challenge_script.js'} ({len(script_body):,} bytes)")

    report = {
        "url": args.url,
        "incident_id": incident_id,
        "iframe_src": full_script_url,
        "outer_page_status": result["status"],
    }

    if script_body.strip().startswith("<"):
        # The iframe src itself served HTML (e.g. a CAPTCHA page), not JS.
        print("\n[*] The iframe resource is HTML, not JavaScript (likely a CAPTCHA/interstitial page).")
        inner_iframe = find_iframe_src(script_body)
        if inner_iframe:
            print(f"    Nested iframe src: {inner_iframe} (re-run pointed at this if you need to go further)")
        report["analysis"] = None
        report["note"] = "iframe resource was HTML, not JS - see nested src if present"
    else:
        report["analysis"] = run_static_analysis(script_body, "Challenge script (from iframe)")

    (save_dir / "crack_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\n✓ Full report saved to {save_dir / 'crack_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
