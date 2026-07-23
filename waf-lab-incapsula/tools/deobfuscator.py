#!/usr/bin/env python3
"""
JavaScript obfuscation analysis and deobfuscation tool.

Handles common obfuscation patterns found in WAF sensors:
- Hex-encoded string arrays (\x** escape sequences)
- Base64 encoded payloads
- Array index mapping (a[b] where b shifts indices)
- RC4 decryption patterns
- Anti-debugging checks
"""

import re
import base64
import sys
import json
from typing import Dict, List, Tuple, Any


class JSDeobfuscator:
    """Analyzes and deobfuscates obfuscated JavaScript."""

    def __init__(self, code: str):
        self.code = code
        self.decoded_strings: Dict[int, str] = {}
        self.suspicious_patterns = []

    def decode_hex_escape_sequences(self) -> Dict[int, str]:
        """
        Extract and decode hex escape sequences (\x**).
        Common in array-based string obfuscation.
        """
        # Find all \x** patterns
        hex_pattern = r"\\x([0-9a-fA-F]{2})"
        matches = re.findall(hex_pattern, self.code)

        # Convert hex to ASCII
        decoded = {}
        for i, hex_byte in enumerate(matches):
            char = chr(int(hex_byte, 16))
            decoded[i] = char

        self.decoded_strings = decoded
        return decoded

    def extract_string_arrays(self) -> List[str]:
        """
        Extract and decode string arrays.
        Pattern: var _0x**** = ['\\x**\\x**', '\\x**\\x**', ...]
        """
        # Match array declarations
        array_pattern = r"var\s+_0x[a-f0-9]+\s*=\s*\[(.*?)\]"
        matches = re.findall(array_pattern, self.code, re.DOTALL)

        decoded_arrays = []
        for array_content in matches:
            # Extract individual strings
            strings = re.findall(r"'([^']*)'", array_content)
            decoded_strs = []

            for s in strings:
                # Decode hex escapes
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
        """
        Detect common WAF sensor evasion and anti-debugging patterns.
        """
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
            "unicode_encoding": r"\\u[0-9a-f]{4}",
            "string_replace": r"\.replace\s*\(\s*/[^/]+/",
        }

        suspicious = []
        for name, pattern in patterns.items():
            matches = re.findall(pattern, self.code, re.IGNORECASE)
            if matches:
                suspicious.append((name, f"Found {len(matches)} occurrence(s)"))

        return suspicious

    def extract_string_mapping(self) -> Dict[str, Any]:
        """
        Extract variable-to-string index mapping.
        Pattern: function _0x**** (a) { return _0x**[a] }
        """
        # Find function definitions that access arrays
        func_pattern = r"function\s+(_0x[a-f0-9]+)\s*\(([^)]*)\)\s*\{[^}]*return\s+_0x([a-f0-9]+)\s*\[\s*\2\s*\]"
        matches = re.findall(func_pattern, self.code)

        mapping = {}
        for func_name, param, array_var in matches:
            mapping[func_name] = {"param": param, "array_ref": array_var}

        return mapping

    def find_base64_payloads(self) -> List[str]:
        """
        Extract Base64-encoded strings (typically 44+ chars ending with ==).
        """
        # Match Base64 patterns (A-Za-z0-9+/= and multiple = at end)
        b64_pattern = r"([A-Za-z0-9+/]{20,}={0,2})"
        matches = re.findall(b64_pattern, self.code)

        payloads = []
        for b64 in matches:
            # Validate it's valid Base64
            try:
                decoded = base64.b64decode(b64, validate=True)
                # If it decodes successfully, it's likely a payload
                payloads.append({"encoded": b64, "decoded": decoded[:100]})
            except Exception:
                pass

        return payloads

    def analyze(self) -> Dict[str, Any]:
        """
        Run full analysis on the obfuscated code.
        """
        return {
            "total_length": len(self.code),
            "hex_sequences": len(self.decode_hex_escape_sequences()),
            "string_arrays": self.extract_string_arrays(),
            "string_mappings": self.extract_string_mapping(),
            "suspicious_patterns": self.detect_suspicious_patterns(),
            "base64_payloads": self.find_base64_payloads(),
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 deobfuscator.py <obfuscated_file.js>")
        print("\nAnalyzes obfuscated JavaScript and extracts deobfuscated content.")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)

    deobf = JSDeobfuscator(code)
    results = deobf.analyze()

    # Pretty print results
    print("=" * 70)
    print("OBFUSCATION ANALYSIS REPORT")
    print("=" * 70)
    print(f"\nFile: {filename}")
    print(f"Total size: {results['total_length']} bytes\n")

    print(f"[*] Hex-encoded strings found: {results['hex_sequences']}")

    print(f"\n[*] String arrays detected: {len(results['string_arrays'])}")
    if results["string_arrays"]:
        for i, array_content in enumerate(results["string_arrays"][:3], 1):
            print(f"\n  Array {i} (first 500 chars):")
            print("  " + "\n  ".join(array_content[:500].split("\n")))
            if len(array_content) > 500:
                print("  ...")

    print(f"\n[*] String accessor mappings: {len(results['string_mappings'])}")
    if results["string_mappings"]:
        for func, mapping in list(results["string_mappings"].items())[:5]:
            print(f"  {func} -> array _0x{mapping['array_ref']}")

    print(f"\n[*] Suspicious patterns detected:")
    for pattern, desc in results["suspicious_patterns"]:
        print(f"  - {pattern}: {desc}")

    print(f"\n[*] Base64 payloads found: {len(results['base64_payloads'])}")
    if results["base64_payloads"]:
        for i, payload in enumerate(results["base64_payloads"][:3], 1):
            print(f"  Payload {i}: {payload['encoded'][:50]}...")
            try:
                print(f"    Decoded: {payload['decoded']}")
            except Exception:
                pass

    print("\n" + "=" * 70)
    print("Extracted strings have been analyzed. See detailed output above.")
    print("=" * 70)


if __name__ == "__main__":
    main()
