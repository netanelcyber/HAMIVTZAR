#!/usr/bin/env python3
"""
RC4 decryption tool for analyzing obfuscated WAF sensor payloads.

RC4 is commonly used in obfuscated bot-detection and anti-automation scripts.
This tool extracts and decrypts RC4-encoded payloads found in JavaScript.
"""

import re
import base64
import sys
from typing import List, Tuple, Optional


class RC4:
    """RC4 cipher implementation for decryption."""

    def __init__(self, key: bytes):
        """Initialize RC4 with a key."""
        self.state = list(range(256))
        j = 0
        for i in range(256):
            j = (j + self.state[i] + key[i % len(key)]) % 256
            self.state[i], self.state[j] = self.state[j], self.state[i]
        self.i = 0
        self.j = 0

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt (or encrypt, same operation) data using RC4."""
        result = []
        for byte in data:
            self.i = (self.i + 1) % 256
            self.j = (self.j + self.state[self.i]) % 256
            self.state[self.i], self.state[self.j] = (
                self.state[self.j],
                self.state[self.i],
            )
            K = self.state[(self.state[self.i] + self.state[self.j]) % 256]
            result.append(byte ^ K)
        return bytes(result)


class PayloadAnalyzer:
    """Analyzes and decrypts obfuscated sensor payloads."""

    def __init__(self, code: str):
        self.code = code
        self.payloads: List[Tuple[str, str]] = []
        self.rc4_keys: List[str] = []

    def extract_base64_payloads(self) -> List[str]:
        """Extract base64-encoded strings from code."""
        # Match base64 patterns (roughly 44+ characters with padding)
        pattern = r'([A-Za-z0-9+/]{20,}={0,2})'
        matches = re.findall(pattern, self.code)

        valid_b64 = []
        for match in matches:
            try:
                decoded = base64.b64decode(match, validate=True)
                # Only include if it decodes to something reasonable
                if len(decoded) > 4:
                    valid_b64.append(match)
            except Exception:
                pass

        return valid_b64

    def extract_hex_strings(self) -> List[str]:
        """Extract hex-encoded strings."""
        # Match \xHH patterns
        pattern = r"((?:\\x[0-9a-fA-F]{2})+)"
        matches = re.findall(pattern, self.code)

        decoded = []
        for match in matches:
            hex_bytes = re.findall(r"\\x([0-9a-fA-F]{2})", match)
            if hex_bytes:
                string = "".join(chr(int(b, 16)) for b in hex_bytes)
                if len(string) > 3:
                    decoded.append(string)

        return decoded

    def find_rc4_indicators(self) -> List[str]:
        """Find patterns that indicate RC4 usage."""
        indicators = [
            r"KSA",  # Key Scheduling Algorithm
            r"PRGA",  # Pseudo-Random Generation Algorithm
            r"0x100",  # Typical RC4 state size
            r"0xff",  # Byte masking
            r"charCodeAt",  # Char code iteration
            r"fromCharCode",  # Building decrypted string
        ]

        found = []
        for pattern in indicators:
            if re.search(pattern, self.code, re.IGNORECASE):
                found.append(pattern)

        return found

    def extract_possible_keys(self) -> List[str]:
        """Extract strings that might be RC4 keys."""
        # Look for strings passed to decryption functions
        # Pattern: function_name(string1, string2) where string2 is likely the key
        pattern = r"function\s*\w+\s*\([^)]*\)\s*\{[^}]*(?:RC4|decrypt|atob)\s*\([^,]+,\s*(['\"])([^'\"]+)\1"
        matches = re.findall(pattern, self.code)

        return [match[1] for match in matches]

    def try_decrypt_base64(self, payload_b64: str, key: str) -> Optional[str]:
        """Try to decrypt a base64-encoded payload with RC4."""
        try:
            encoded = base64.b64decode(payload_b64)
            rc4 = RC4(key.encode())
            decrypted = rc4.decrypt(encoded)

            # Try to decode as UTF-8
            try:
                return decrypted.decode("utf-8", errors="ignore")
            except Exception:
                # Return as hex if not valid UTF-8
                return decrypted.hex()
        except Exception:
            return None

    def analyze(self) -> dict:
        """Run full analysis."""
        return {
            "base64_payloads": self.extract_base64_payloads(),
            "hex_strings": self.extract_hex_strings(),
            "rc4_indicators": self.find_rc4_indicators(),
            "possible_keys": self.extract_possible_keys(),
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 rc4_decryptor.py <obfuscated_file.js> [rc4_key]")
        print("\nAnalyzes obfuscated JavaScript for RC4 encryption patterns.")
        print("Optional: provide RC4 key to attempt decryption.")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)

    analyzer = PayloadAnalyzer(code)
    results = analyzer.analyze()

    print("=" * 70)
    print("RC4 ENCRYPTION ANALYSIS REPORT")
    print("=" * 70)
    print(f"\nFile: {filename}\n")

    print(f"[*] RC4 Indicators Found: {len(results['rc4_indicators'])}")
    for indicator in results["rc4_indicators"]:
        print(f"    - {indicator}")

    print(f"\n[*] Base64 Payloads Found: {len(results['base64_payloads'])}")
    if results["base64_payloads"]:
        for i, payload in enumerate(results["base64_payloads"][:5], 1):
            print(f"  Payload {i}: {payload[:60]}...")

    print(f"\n[*] Hex-Encoded Strings Found: {len(results['hex_strings'])}")
    if results["hex_strings"]:
        for i, string in enumerate(results["hex_strings"][:5], 1):
            print(f"  String {i}: {string[:60]}...")

    print(f"\n[*] Possible RC4 Keys: {len(results['possible_keys'])}")
    if results["possible_keys"]:
        for i, key in enumerate(results["possible_keys"][:5], 1):
            print(f"  Key {i}: {key}")

    # If key provided, attempt decryption
    if len(sys.argv) > 2:
        key = sys.argv[2]
        print(f"\n[*] Attempting RC4 decryption with key: {key}")
        print("-" * 70)

        for i, payload in enumerate(results["base64_payloads"][:3], 1):
            decrypted = analyzer.try_decrypt_base64(payload, key)
            if decrypted:
                print(f"\nPayload {i} (decrypted):")
                print(decrypted[:500])
                if len(decrypted) > 500:
                    print("...")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
