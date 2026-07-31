#!/usr/bin/env python3
"""
FortiOS Binary Comparison Tool: Build 0030 vs Build 0167
Automated binary analysis for vulnerability persistence
"""

import os
import sys
import json
import hashlib
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class BinaryComparator:
    """Compare two FortiOS binaries to identify code changes"""

    def __init__(self, binary_0030_path: str, binary_0167_path: str):
        """Initialize comparator with binary paths"""
        self.binary_0030_path = Path(binary_0030_path)
        self.binary_0167_path = Path(binary_0167_path)
        self.results = {
            "binary_0030": str(self.binary_0030_path),
            "binary_0167": str(self.binary_0167_path),
            "comparison": {}
        }

    def verify_binaries_exist(self) -> bool:
        """Check if both binaries are accessible"""
        if not self.binary_0030_path.exists():
            print(f"ERROR: Binary 0030 not found at {self.binary_0030_path}")
            return False
        if not self.binary_0167_path.exists():
            print(f"ERROR: Binary 0167 not found at {self.binary_0167_path}")
            return False
        return True

    def calculate_binary_hash(self, binary_path: Path) -> str:
        """Calculate SHA256 hash of binary"""
        sha256_hash = hashlib.sha256()
        with open(binary_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def compare_binaries(self) -> Dict:
        """Perform comprehensive binary comparison"""
        print("[*] Starting binary comparison...")

        if not self.verify_binaries_exist():
            return self.results

        # Calculate file sizes
        size_0030 = self.binary_0030_path.stat().st_size
        size_0167 = self.binary_0167_path.stat().st_size

        # Calculate hashes
        hash_0030 = self.calculate_binary_hash(self.binary_0030_path)
        hash_0167 = self.calculate_binary_hash(self.binary_0167_path)

        self.results["comparison"]["file_comparison"] = {
            "build_0030": {
                "size_bytes": size_0030,
                "sha256": hash_0030
            },
            "build_0167": {
                "size_bytes": size_0167,
                "sha256": hash_0167
            },
            "are_identical": hash_0030 == hash_0167,
            "size_difference_bytes": abs(size_0167 - size_0030)
        }

        print(f"[+] Build 0030 size: {size_0030:,} bytes")
        print(f"[+] Build 0167 size: {size_0167:,} bytes")
        print(f"[+] Size difference: {abs(size_0167 - size_0030):,} bytes")
        print(f"[+] Binaries identical: {hash_0030 == hash_0167}")

        # Find differing sections
        if size_0030 == size_0167:
            self.find_byte_differences()

        # Search for vulnerable function signatures
        self.find_vulnerable_functions()

        # Analyze string changes
        self.compare_strings()

        # Check for known gadgets
        self.find_rop_gadgets()

        return self.results

    def find_byte_differences(self):
        """Find specific byte-level differences between binaries"""
        print("[*] Scanning for byte-level differences...")

        differences = []
        with open(self.binary_0030_path, "rb") as f1, open(self.binary_0167_path, "rb") as f2:
            offset = 0
            while True:
                chunk1 = f1.read(4096)
                chunk2 = f2.read(4096)

                if not chunk1 or not chunk2:
                    break

                for i, (byte1, byte2) in enumerate(zip(chunk1, chunk2)):
                    if byte1 != byte2:
                        differences.append({
                            "offset": hex(offset + i),
                            "value_0030": hex(byte1),
                            "value_0167": hex(byte2)
                        })

                offset += len(chunk1)

        self.results["comparison"]["byte_differences"] = {
            "total_differences": len(differences),
            "first_10_differences": differences[:10]
        }

        print(f"[+] Found {len(differences)} byte-level differences")

    def find_vulnerable_functions(self):
        """Search for known vulnerable function signatures"""
        print("[*] Searching for vulnerable function signatures...")

        vulnerable_functions = {
            "path_handler": {
                "signature": b"path_handler",
                "vulnerable_in_0030": True
            },
            "process_hostname": {
                "signature": b"process_hostname",
                "vulnerable_in_0030": True
            },
            "validate_session": {
                "signature": b"validate_session",
                "vulnerable_in_0030": True
            },
            "format_log_entry": {
                "signature": b"format_log_entry",
                "vulnerable_in_0030": True
            },
            "handle_connection": {
                "signature": b"handle_connection",
                "vulnerable_in_0030": True
            }
        }

        results = {"functions_found": {}, "functions_missing": []}

        for func_name, func_data in vulnerable_functions.items():
            found_0030 = self.search_function_signature(self.binary_0030_path, func_data["signature"])
            found_0167 = self.search_function_signature(self.binary_0167_path, func_data["signature"])

            if found_0030 or found_0167:
                results["functions_found"][func_name] = {
                    "found_in_0030": found_0030,
                    "found_in_0167": found_0167,
                    "patched": found_0030 and not found_0167,
                    "address_0030": found_0030,
                    "address_0167": found_0167
                }
            else:
                results["functions_missing"].append(func_name)

        self.results["comparison"]["vulnerable_functions"] = results
        print(f"[+] Found {len(results['functions_found'])} vulnerable functions")

    def search_function_signature(self, binary_path: Path, signature: bytes) -> Optional[str]:
        """Search for function signature in binary"""
        with open(binary_path, "rb") as f:
            content = f.read()
            index = content.find(signature)
            if index != -1:
                return hex(index)
        return None

    def compare_strings(self):
        """Extract and compare string differences"""
        print("[*] Analyzing string differences...")

        strings_0030 = self.extract_strings(self.binary_0030_path)
        strings_0167 = self.extract_strings(self.binary_0167_path)

        added_strings = set(strings_0167) - set(strings_0030)
        removed_strings = set(strings_0030) - set(strings_0167)

        self.results["comparison"]["string_changes"] = {
            "total_strings_0030": len(strings_0030),
            "total_strings_0167": len(strings_0167),
            "strings_added": list(added_strings)[:20],
            "strings_removed": list(removed_strings)[:20],
            "added_count": len(added_strings),
            "removed_count": len(removed_strings)
        }

        print(f"[+] Strings added: {len(added_strings)}")
        print(f"[+] Strings removed: {len(removed_strings)}")

    def extract_strings(self, binary_path: Path, min_length: int = 4) -> List[str]:
        """Extract human-readable strings from binary"""
        strings = []
        with open(binary_path, "rb") as f:
            current_string = b""
            for byte in f.read():
                if 32 <= byte <= 126:  # Printable ASCII
                    current_string += bytes([byte])
                else:
                    if len(current_string) >= min_length:
                        try:
                            strings.append(current_string.decode('ascii'))
                        except:
                            pass
                    current_string = b""
        return strings

    def find_rop_gadgets(self):
        """Search for known ROP gadgets"""
        print("[*] Searching for ROP gadgets...")

        # Known gadgets from Build 0030
        known_gadgets = {
            "POP RDI; RET": b"\x5f\xc3",
            "POP RSI; RET": b"\x5e\xc3",
            "POP RDX; RET": b"\x5a\xc3",
            "POP RAX; RET": b"\x58\xc3"
        }

        gadgets_0030 = {}
        gadgets_0167 = {}

        print("  Searching in Build 0030...")
        for gadget_name, gadget_bytes in known_gadgets.items():
            gadgets_0030[gadget_name] = self.find_all_gadgets(self.binary_0030_path, gadget_bytes)

        print("  Searching in Build 0167...")
        for gadget_name, gadget_bytes in known_gadgets.items():
            gadgets_0167[gadget_name] = self.find_all_gadgets(self.binary_0167_path, gadget_bytes)

        self.results["comparison"]["rop_gadgets"] = {
            "gadgets_0030": {k: len(v) for k, v in gadgets_0030.items()},
            "gadgets_0167": {k: len(v) for k, v in gadgets_0167.items()},
            "gadgets_0030_samples": {k: v[:3] for k, v in gadgets_0030.items()},
            "gadgets_0167_samples": {k: v[:3] for k, v in gadgets_0167.items()},
            "status": "Gadgets located successfully"
        }

        print("[+] ROP gadget analysis complete")

    def find_all_gadgets(self, binary_path: Path, gadget_bytes: bytes) -> List[str]:
        """Find all occurrences of a gadget in binary"""
        gadgets = []
        with open(binary_path, "rb") as f:
            content = f.read()
            offset = 0
            while True:
                index = content.find(gadget_bytes, offset)
                if index == -1:
                    break
                gadgets.append(hex(index))
                offset = index + 1
        return gadgets

    def export_results(self, output_file: Optional[str] = None) -> Path:
        """Export comparison results to JSON"""
        if not output_file:
            output_file = "binary_comparison_results.json"

        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"[+] Results exported to: {output_path}")
        return output_path

    def generate_report(self) -> str:
        """Generate human-readable comparison report"""
        report = """
================================================================================
FortiOS Binary Comparison Report: Build 0030 vs Build 0167
================================================================================

FILE COMPARISON:
"""
        comparison = self.results.get("comparison", {})
        file_comp = comparison.get("file_comparison", {})

        report += f"Build 0030 Size: {file_comp.get('build_0030', {}).get('size_bytes', 'N/A'):,} bytes\n"
        report += f"Build 0167 Size: {file_comp.get('build_0167', {}).get('size_bytes', 'N/A'):,} bytes\n"
        report += f"Size Difference: {file_comp.get('size_difference_bytes', 'N/A'):,} bytes\n"
        report += f"Binaries Identical: {file_comp.get('are_identical', 'N/A')}\n"

        report += "\nVULNERABLE FUNCTIONS:\n"
        for func_name, func_info in comparison.get("vulnerable_functions", {}).get("functions_found", {}).items():
            status = "PATCHED" if func_info.get("patched") else "VULNERABLE"
            report += f"  {func_name}: {status}\n"

        report += "\nROP GADGETS:\n"
        rop_gadgets = comparison.get("rop_gadgets", {})
        for gadget_name, count in rop_gadgets.get("gadgets_0030", {}).items():
            count_0167 = rop_gadgets.get("gadgets_0167", {}).get(gadget_name, 0)
            report += f"  {gadget_name}: {count} (0030) → {count_0167} (0167)\n"

        report += "\n" + "="*80 + "\n"
        report += "INTERPRETATION GUIDE:\n"
        report += "- If functions REMOVED: Vulnerability likely PATCHED\n"
        report += "- If functions PRESENT: Check for code changes\n"
        report += "- If ROP gadgets CHANGED: Exploitation chains need adjustment\n"
        report += "- If binaries IDENTICAL: Vulnerabilities persist unchanged\n"
        report += "="*80 + "\n"

        return report

def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python3 binary_comparison_tool.py <binary_0030_path> <binary_0167_path>")
        print("Example: python3 binary_comparison_tool.py fortios_0030.bin fortios_0167.bin")
        sys.exit(1)

    binary_0030 = sys.argv[1]
    binary_0167 = sys.argv[2]

    comparator = BinaryComparator(binary_0030, binary_0167)
    results = comparator.compare_binaries()

    # Print report
    print(comparator.generate_report())

    # Export results
    comparator.export_results()

if __name__ == "__main__":
    main()
