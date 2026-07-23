"""
WAF Sensor Analysis Toolkit for Google Colab
Analyze obfuscated bot-detection scripts (Imperva/Incapsula, Cloudflare, etc.)
"""

# Install requirements
# !pip install requests beautifulsoup4 lxml

import re
import base64
import json
from typing import Dict, List, Tuple, Any

class JSDeobfuscator:
    """Analyzes and deobfuscates obfuscated JavaScript."""

    def __init__(self, code: str):
        self.code = code
        self.decoded_strings: Dict[int, str] = {}
        self.suspicious_patterns = []

    def decode_hex_escape_sequences(self) -> Dict[int, str]:
        """Extract and decode hex escape sequences (\\x**)."""
        hex_pattern = r"\\x([0-9a-fA-F]{2})"
        matches = re.findall(hex_pattern, self.code)

        decoded = {}
        for i, hex_byte in enumerate(matches):
            char = chr(int(hex_byte, 16))
            decoded[i] = char

        self.decoded_strings = decoded
        return decoded

    def extract_string_arrays(self) -> List[str]:
        """Extract and decode string arrays."""
        array_pattern = r"var\s+_0x[a-f0-9]+\s*=\s*\[(.*?)\]"
        matches = re.findall(array_pattern, self.code, re.DOTALL)

        decoded_arrays = []
        for array_content in matches:
            strings = re.findall(r"'([^']*)'", array_content)
            decoded_strs = []

            for s in strings:
                decoded = re.sub(
                    r"\\x([0-9a-fA-F]{2})",
                    lambda m: chr(int(m.group(1), 16)),
                    s,
                )
                decoded_strs.append(decoded)

            if decoded_strs:
                decoded_arrays.append("\n".join(decoded_strs))

        return decoded_arrays

    def detect_suspicious_patterns(self) -> List[Tuple[str, str]]:
        """Detect common WAF sensor evasion and anti-debugging patterns."""
        patterns = {
            "debugger": r"debugger\s*;",
            "console_disable": r"console\s*=\s*[{}]",
            "eval": r"\beval\s*\(",
            "Function": r"\bFunction\s*\(",
            "webdriver_check": r"navigator\.webdriver",
            "headless_detect": r"HeadlessChrome|PhantomJS|webdriver",
            "chrome_detect": r"chrome\.runtime|webextension",
            "proxy_detect": r"proxy|bypass|automation",
            "base64_decode": r"atob\s*\(",
            "base64_encode": r"btoa\s*\(",
            "rc4_ksa": r"KSA|RC4|ksa",
            "hex_encoding": r"\\x[0-9a-f]{2}",
        }

        suspicious = []
        for name, pattern in patterns.items():
            matches = re.findall(pattern, self.code, re.IGNORECASE)
            if matches:
                suspicious.append((name, f"Found {len(matches)} occurrence(s)"))

        return suspicious

    def analyze(self) -> Dict[str, Any]:
        """Run full analysis on the obfuscated code."""
        return {
            "total_length": len(self.code),
            "hex_sequences": len(self.decode_hex_escape_sequences()),
            "string_arrays": self.extract_string_arrays(),
            "suspicious_patterns": self.detect_suspicious_patterns(),
        }


class AntiDetectionAnalyzer:
    """Analyzes code for anti-detection and anti-automation patterns."""

    DETECTION_PATTERNS = {
        "headless_browser": {
            "patterns": [r"HeadlessChrome", r"navigator\.webdriver", r"PhantomJS"],
            "description": "Detects headless browser execution",
            "bypass": "Override User-Agent, patch navigator.webdriver",
        },
        "browser_automation": {
            "patterns": [r"webdriver", r"selenium", r"puppeteer", r"playwright"],
            "description": "Detects browser automation tools",
            "bypass": "Use stealth plugins, patch navigator properties",
        },
        "nodejs_detection": {
            "patterns": [r"process\.env", r"require\s*\(", r"__dirname"],
            "description": "Detects Node.js environment",
            "bypass": "Use browser environment (Playwright headless)",
        },
        "timing_attacks": {
            "patterns": [r"setTimeout", r"performance\.timing", r"Date\.now\(\)"],
            "description": "Uses timing analysis to detect automation",
            "bypass": "Override timing functions to return consistent values",
        },
        "console_disable": {
            "patterns": [r"console\s*=\s*\{\}", r"console\.log\s*="],
            "description": "Disables console for anti-debugging",
            "bypass": "Restore console before code runs",
        },
        "eval_detection": {
            "patterns": [r"eval\s*\(", r"Function\s*\("],
            "description": "Uses eval to dynamically load code",
            "bypass": "Analyze eval'd code separately or patch eval",
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


# ============================================================================
# COLAB USAGE EXAMPLES
# ============================================================================

def analyze_sensor_url(url: str):
    """Download and analyze a sensor script from URL."""
    import requests
    
    print(f"📥 Downloading from {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    code = response.text
    print(f"✓ Downloaded {len(code)} bytes\n")
    
    return analyze_code(code)


def analyze_code(code: str):
    """Analyze JavaScript code for obfuscation and detection mechanisms."""
    
    print("="*80)
    print("ANTI-DETECTION ANALYSIS")
    print("="*80)
    
    detector = AntiDetectionAnalyzer(code)
    findings = detector.analyze()
    strategies = detector.get_bypass_strategies()
    
    if not findings:
        print("✓ No obvious anti-detection patterns found")
    else:
        print(f"\n⚠️  Found {len(findings)} detection mechanism(s):\n")
        for i, (check_name, patterns) in enumerate(findings.items(), 1):
            print(f"{i}. {check_name.upper().replace('_', ' ')}")
            print(f"   Patterns: {', '.join(patterns[:2])}")
            print(f"   Bypass:   {strategies.get(check_name, 'N/A')}\n")
    
    print("\n" + "="*80)
    print("OBFUSCATION ANALYSIS")
    print("="*80 + "\n")
    
    deobf = JSDeobfuscator(code)
    results = deobf.analyze()
    
    print(f"File size: {results['total_length']} bytes")
    print(f"Hex-encoded strings: {results['hex_sequences']}")
    print(f"String arrays detected: {len(results['string_arrays'])}")
    
    if results['string_arrays']:
        print("\n📋 Decoded Strings (first array):")
        first_array = results['string_arrays'][0].split('\n')[:10]
        for i, s in enumerate(first_array, 1):
            print(f"  {i}. {s[:60]}")
    
    print(f"\n🚨 Suspicious patterns:")
    for pattern, desc in results['suspicious_patterns']:
        print(f"  - {pattern}: {desc}")
    
    return {
        'detections': findings,
        'obfuscation': results
    }


# ============================================================================
# IN COLAB, USE LIKE THIS:
# ============================================================================
#
# # Example 1: Analyze sample code
# sample_code = '''
# var _0x1234 = ['\\x63\\x6f\\x6f\\x6b\\x69\\x65', '\\x74\\x6f\\x6b\\x65\\x6e'];
# console.log = function() {};
# if (navigator.webdriver) alert('detected');
# '''
# analyze_code(sample_code)
#
# # Example 2: Analyze from URL
# analyze_sensor_url('https://cdn.example.com/sensor.js')
#
# # Example 3: Upload file
# from google.colab import files
# uploaded = files.upload()
# filename = list(uploaded.keys())[0]
# with open(filename) as f:
#     code = f.read()
# analyze_code(code)
#

