"""Tests for the PACS ISO 27799 compliance-audit toolkit.

Fully offline: this module only scores a JSON config dict against the
control catalog. It never opens a network connection.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pacs_iso27799_audit.audit import (
    evaluate_control,
    render_markdown_report,
    run_audit,
    summarize,
)
from pacs_iso27799_audit.controls import CONTROLS, DOMAINS


class ControlCatalogTests(unittest.TestCase):
    def test_every_control_has_a_known_domain(self):
        for c in CONTROLS:
            self.assertIn(c.domain, DOMAINS)

    def test_automated_controls_have_config_fields(self):
        for c in CONTROLS:
            if c.check_type == "automated":
                self.assertIsNotNone(c.config_path)
                self.assertIsNotNone(c.operator)

    def test_manual_controls_have_no_config_path(self):
        for c in CONTROLS:
            if c.check_type == "manual":
                self.assertIsNone(c.config_path)

    def test_control_ids_are_unique(self):
        ids = [c.id for c in CONTROLS]
        self.assertEqual(len(ids), len(set(ids)))


class EvaluateControlTests(unittest.TestCase):
    def test_truthy_pass(self):
        control = next(c for c in CONTROLS if c.id == "AC-2")  # rbac_enabled truthy True
        result = evaluate_control(control, {"access_control": {"rbac_enabled": True}})
        self.assertEqual(result.status, "pass")

    def test_truthy_fail(self):
        control = next(c for c in CONTROLS if c.id == "AC-2")
        result = evaluate_control(control, {"access_control": {"rbac_enabled": False}})
        self.assertEqual(result.status, "fail")

    def test_eq_false_expected_pass(self):
        control = next(c for c in CONTROLS if c.id == "AC-1")  # shared_accounts_allowed eq False
        result = evaluate_control(control, {"access_control": {"shared_accounts_allowed": False}})
        self.assertEqual(result.status, "pass")

    def test_le_threshold(self):
        control = next(c for c in CONTROLS if c.id == "AC-4")  # idle timeout <= 15
        pass_result = evaluate_control(control, {"access_control": {"session_idle_timeout_minutes": 10}})
        fail_result = evaluate_control(control, {"access_control": {"session_idle_timeout_minutes": 30}})
        self.assertEqual(pass_result.status, "pass")
        self.assertEqual(fail_result.status, "fail")

    def test_ge_threshold(self):
        control = next(c for c in CONTROLS if c.id == "AC-5")  # password_min_length >= 12
        pass_result = evaluate_control(control, {"access_control": {"password_min_length": 14}})
        fail_result = evaluate_control(control, {"access_control": {"password_min_length": 8}})
        self.assertEqual(pass_result.status, "pass")
        self.assertEqual(fail_result.status, "fail")

    def test_missing_config_key(self):
        control = next(c for c in CONTROLS if c.id == "CR-1")
        result = evaluate_control(control, {})
        self.assertEqual(result.status, "missing_data")

    def test_manual_control_always_flagged(self):
        control = next(c for c in CONTROLS if c.check_type == "manual")
        result = evaluate_control(control, {"anything": True})
        self.assertEqual(result.status, "manual_review")


class RunAuditTests(unittest.TestCase):
    def test_run_audit_covers_every_control(self):
        results = run_audit({})
        self.assertEqual(len(results), len(CONTROLS))

    def test_summarize_counts_add_up(self):
        results = run_audit({})
        counts = summarize(results)
        self.assertEqual(sum(counts.values()), len(CONTROLS))

    def test_sample_config_file_is_valid_and_scoreable(self):
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "pacs_iso27799_audit", "sample_config.json",
        )
        with open(sample_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        results = run_audit(config)
        self.assertEqual(len(results), len(CONTROLS))
        counts = summarize(results)
        self.assertGreater(counts["pass"], 0)
        self.assertGreater(counts["fail"], 0)
        self.assertGreater(counts["manual_review"], 0)


class ReportRenderingTests(unittest.TestCase):
    def test_markdown_report_contains_disclaimer_and_all_controls(self):
        results = run_audit({})
        report = render_markdown_report(results, "Test Report")
        self.assertIn("Test Report", report)
        self.assertIn("not a substitute for a qualified ISO 27799 assessor", report)
        for c in CONTROLS:
            self.assertIn(c.id, report)


if __name__ == "__main__":
    unittest.main()
