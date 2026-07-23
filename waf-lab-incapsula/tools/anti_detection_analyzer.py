#!/usr/bin/env python3
"""
Anti-Detection Pattern Analyzer

Identifies bot-detection and anti-automation checks in obfuscated JavaScript.
Useful for understanding what detection mechanisms need to be bypassed.
"""

import re
import sys
import json
from typing import Dict, List


class AntiDetectionAnalyzer:
    """Analyzes code for anti-detection and anti-automation patterns."""

    # Detection patterns mapped to what they check
    DETECTION_PATTERNS = {
        "headless_browser": {
            "patterns": [
                r"HeadlessChrome",
                r"navigator\.webdriver",
                r"PhantomJS",
                r"phantomjs",
                r"headless",
            ],
            "description": "Detects headless browser execution",
            "bypass": "Override User-Agent, patch navigator.webdriver",
        },
        "browser_automation": {
            "patterns": [
                r"webdriver",
                r"selenium",
                r"puppeteer",
                r"nightmare",
                r"playwright",
                r"automation",
            ],
            "description": "Detects browser automation tools",
            "bypass": "Use stealth plugins, patch navigator properties",
        },
        "chrome_extension": {
            "patterns": [
                r"chrome\.runtime",
                r"chrome\.extension",
                r"webextension",
            ],
            "description": "Detects Chrome extension context",
            "bypass": "Run in regular browser, not extension context",
        },
        "nodejs_detection": {
            "patterns": [
                r"process\.env",
                r"require\s*\(",
                r"__dirname",
                r"__filename",
                r"exports",
                r"module\.exports",
            ],
            "description": "Detects Node.js environment",
            "bypass": "Use browser environment (Playwright headless)",
        },
        "proxy_detection": {
            "patterns": [
                r"proxy",
                r"bypass",
                r"vpn",
                r"tor",
            ],
            "description": "May detect proxy or VPN usage",
            "bypass": "Use legitimate ISP or proxies that don't have signatures",
        },
        "timing_attacks": {
            "patterns": [
                r"setTimeout",
                r"setInterval",
                r"performance\.timing",
                r"Date\.now\(\)",
                r"PerformanceObserver",
            ],
            "description": "Uses timing analysis to detect automation",
            "bypass": "Override timing functions to return consistent values",
        },
        "geolocation_check": {
            "patterns": [
                r"geolocation",
                r"latitude",
                r"longitude",
                r"ip\s*check",
                r"geoip",
            ],
            "description": "Checks geolocation data",
            "bypass": "Spoof geolocation in browser, use matching IP location",
        },
        "device_fingerprint": {
            "patterns": [
                r"canvas.*fingerprint",
                r"webgl",
                r"audioContext",
                r"devicePixelRatio",
                r"screen\.width",
                r"screen\.height",
            ],
            "description": "Builds device fingerprint",
            "bypass": "Use consistent device properties, real browser",
        },
        "console_disable": {
            "patterns": [
                r"console\s*=\s*\{\}",
                r"console\.log\s*=",
                r"console\.error\s*=",
            ],
            "description": "Disables console for anti-debugging",
            "bypass": "Restore console before code runs",
        },
        "eval_detection": {
            "patterns": [
                r"eval\s*\(",
                r"Function\s*\(",
                r"indirect eval",
            ],
            "description": "Uses eval to dynamically load code",
            "bypass": "Analyze eval'd code separately or patch eval",
        },
        "debugger_detection": {
            "patterns": [
                r"debugger\s*;",
                r"Function\.prototype\.constructor",
                r"toString\(\)",
            ],
            "description": "Detects debugger or breakpoints",
            "bypass": "Disable breakpoints, skip debugger statements",
        },
        "websocket_check": {
            "patterns": [
                r"WebSocket",
                r"ws://",
                r"wss://",
            ],
            "description": "May detect WebSocket-based communication",
            "bypass": "Intercept WebSocket or use regular HTTP",
        },
        "local_storage_check": {
            "patterns": [
                r"localStorage",
                r"sessionStorage",
                r"IndexedDB",
            ],
            "description": "Checks browser storage for detection markers",
            "bypass": "Clear storage or mock storage methods",
        },
        "cookie_check": {
            "patterns": [
                r"document\.cookie",
                r"setCookie",
                r"getCookie",
            ],
            "description": "Checks or sets tracking cookies",
            "bypass": "Handle cookies as expected",
        },
    }

    def __init__(self, code: str):
        self.code = code
        self.findings: Dict[str, List[str]] = {}

    def analyze(self) -> Dict[str, List[str]]:
        """Run analysis on the code."""
        for check_name, check_info in self.DETECTION_PATTERNS.items():
            matches = []
            for pattern in check_info["patterns"]:
                found = re.findall(pattern, self.code, re.IGNORECASE)
                if found:
                    matches.extend(found)

            if matches:
                self.findings[check_name] = list(set(matches))

        return self.findings

    def get_bypass_strategies(self) -> Dict[str, str]:
        """Get bypass strategies for detected checks."""
        strategies = {}
        for check_name in self.findings:
            if check_name in self.DETECTION_PATTERNS:
                strategies[check_name] = (
                    self.DETECTION_PATTERNS[check_name]["bypass"]
                )
        return strategies

    def get_descriptions(self) -> Dict[str, str]:
        """Get descriptions of detected checks."""
        descriptions = {}
        for check_name in self.findings:
            if check_name in self.DETECTION_PATTERNS:
                descriptions[check_name] = (
                    self.DETECTION_PATTERNS[check_name]["description"]
                )
        return descriptions


def print_report(analyzer: AntiDetectionAnalyzer):
    """Print detailed analysis report."""
    findings = analyzer.analyze()
    bypass_strategies = analyzer.get_bypass_strategies()
    descriptions = analyzer.get_descriptions()

    print("=" * 80)
    print("ANTI-DETECTION & BOT-DETECTION ANALYSIS REPORT")
    print("=" * 80)

    if not findings:
        print("\n[*] No obvious anti-detection patterns found.")
        print("    (This doesn't mean there are no checks - they might be obfuscated)")
        return

    print(f"\n[!] Found {len(findings)} detection mechanism(s):\n")

    for i, (check_name, matched_strings) in enumerate(findings.items(), 1):
        print(f"{i}. {check_name.upper().replace('_', ' ')}")
        print(f"   Description: {descriptions.get(check_name, 'N/A')}")
        print(f"   Detected patterns: {', '.join(matched_strings[:3])}")
        if len(matched_strings) > 3:
            print(f"                      (+ {len(matched_strings) - 3} more)")
        print(f"   Bypass strategy:  {bypass_strategies.get(check_name, 'N/A')}")
        print()

    # Print prioritized bypass plan
    print("=" * 80)
    print("RECOMMENDED BYPASS PRIORITY")
    print("=" * 80)
    print("\n[Priority 1 - Critical]")
    for check in ["headless_browser", "browser_automation", "nodejs_detection"]:
        if check in findings:
            print(f"  • {check.replace('_', ' ').title()}")

    print("\n[Priority 2 - Important]")
    for check in ["navigator_check", "console_disable", "timing_attacks"]:
        if check in findings:
            print(f"  • {check.replace('_', ' ').title()}")

    print("\n[Priority 3 - Optional]")
    for check in findings:
        if check not in [
            "headless_browser",
            "browser_automation",
            "nodejs_detection",
            "navigator_check",
            "console_disable",
            "timing_attacks",
        ]:
            print(f"  • {check.replace('_', ' ').title()}")

    # Print implementation suggestions
    print("\n" + "=" * 80)
    print("IMPLEMENTATION SUGGESTIONS")
    print("=" * 80)

    if "headless_browser" in findings or "browser_automation" in findings:
        print("\n1. Use real browser context:")
        print(
            "   ```python\n"
            "   from playwright.async_api import async_playwright\n"
            "   browser = await p.chromium.launch(headless=True)\n"
            "   context = await browser.new_context()\n"
            "   await context.add_init_script(\n"
            "       'Object.defineProperty(navigator, \"webdriver\", "
            "{get: () => undefined})'\n"
            "   )\n"
            "   ```"
        )

    if "nodejs_detection" in findings:
        print("\n2. Avoid Node.js/Puppeteer, use browser-based solution:")
        print(
            "   ```python\n"
            "   # Use Playwright with chromium instead\n"
            "   # Avoid sending typical Node.js headers\n"
            "   ```"
        )

    if "console_disable" in findings:
        print("\n3. Restore console before/around code execution:")
        print(
            "   ```javascript\n"
            "   window.console = {log: console_log, error: console_error};\n"
            "   ```"
        )

    if "cookie_check" in findings:
        print("\n4. Handle cookies correctly:")
        print(
            "   ```python\n"
            "   # Check what cookies the page expects\n"
            "   # Mimic the challenge response format\n"
            "   ```"
        )


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 anti_detection_analyzer.py <obfuscated_file.js>")
        print("\nAnalyzes obfuscated code for anti-detection mechanisms.")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)

    analyzer = AntiDetectionAnalyzer(code)
    print_report(analyzer)

    # Optional: output JSON for programmatic use
    findings = analyzer.analyze()
    bypass_strategies = analyzer.get_bypass_strategies()

    report = {
        "detections_found": len(findings),
        "detection_types": findings,
        "bypass_strategies": bypass_strategies,
    }

    print("\n" + "=" * 80)
    print("JSON OUTPUT (for programmatic use)")
    print("=" * 80)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
