"""Tests for the ISO 27001 book's offline CWE risk calculator.

Run fully offline -- no API key or network required.
"""

import os
import sys
import unittest

TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "iso27001-book", "tools"
)
sys.path.insert(0, TOOLS_DIR)

from cwe_risk_calculator import CWE_BASELINE, Finding, compute_score, risk_level


class ComputeScoreTests(unittest.TestCase):
    def test_multiplies_likelihood_by_impact(self):
        self.assertEqual(compute_score(4, 5), 20)
        self.assertEqual(compute_score(1, 1), 1)

    def test_rejects_out_of_range_values(self):
        with self.assertRaises(ValueError):
            compute_score(0, 3)
        with self.assertRaises(ValueError):
            compute_score(3, 6)


class RiskLevelTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(risk_level(1), "נמוך (Low)")
        self.assertEqual(risk_level(4), "נמוך (Low)")
        self.assertEqual(risk_level(5), "בינוני (Medium)")
        self.assertEqual(risk_level(9), "בינוני (Medium)")
        self.assertEqual(risk_level(10), "גבוה (High)")
        self.assertEqual(risk_level(16), "גבוה (High)")
        self.assertEqual(risk_level(17), "קריטי (Critical)")
        self.assertEqual(risk_level(25), "קריטי (Critical)")


class FindingResolveTests(unittest.TestCase):
    def test_unknown_cwe_raises(self):
        with self.assertRaises(KeyError):
            Finding(cwe_id="CWE-0").resolve()

    def test_baseline_values_used_when_no_override(self):
        result = Finding(cwe_id="cwe-89").resolve()
        baseline = CWE_BASELINE["CWE-89"]
        self.assertEqual(result["cwe_id"], "CWE-89")
        self.assertEqual(result["likelihood"], baseline["likelihood"])
        expected_impact = max(baseline["impact_c"], baseline["impact_i"], baseline["impact_a"])
        self.assertEqual(result["impact_max"], expected_impact)
        self.assertEqual(result["score"], baseline["likelihood"] * expected_impact)

    def test_overrides_win_over_baseline(self):
        result = Finding(cwe_id="CWE-89", likelihood=1, impact_c=1, impact_i=1, impact_a=1).resolve()
        self.assertEqual(result["likelihood"], 1)
        self.assertEqual(result["impact_max"], 1)
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["risk_level"], "נמוך (Low)")

    def test_every_baseline_entry_is_internally_consistent(self):
        for cwe_id, data in CWE_BASELINE.items():
            for key in ("likelihood", "impact_c", "impact_i", "impact_a"):
                self.assertTrue(1 <= data[key] <= 5, f"{cwe_id}.{key} out of range")


if __name__ == "__main__":
    unittest.main()
