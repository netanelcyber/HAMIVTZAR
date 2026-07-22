"""Tests for the static, offline CVE reference lookup in the holon.muni.il
engagement scaffold (pentest-holon/tools/holon_pentest_all.py).

Fully offline: exercises only the hardcoded CVE_DATABASE and its version-
matching helpers, no network access and nothing sent to any target.
"""

import importlib.util
import os
import unittest

_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "pentest-holon", "tools", "holon_pentest_all.py",
)
_spec = importlib.util.spec_from_file_location("holon_pentest_all", _MODULE_PATH)
holon_pentest_all = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(holon_pentest_all)

parse_dotted_version = holon_pentest_all.parse_dotted_version
fortios_version_ready_for_range_check = holon_pentest_all.fortios_version_ready_for_range_check
fortios_cve_matches = holon_pentest_all.fortios_cve_matches
CVE_DATABASE = holon_pentest_all.CVE_DATABASE

FORTINET_ENTRIES = CVE_DATABASE["fortinet"]


class ParseDottedVersionTests(unittest.TestCase):
    def test_parses_plain_dotted_version(self):
        self.assertEqual(parse_dotted_version("6.4.6"), (6, 4, 6))

    def test_rejects_non_numeric(self):
        self.assertIsNone(parse_dotted_version("6.x.4"))
        self.assertIsNone(parse_dotted_version("abc"))
        self.assertIsNone(parse_dotted_version("6.4.6-beta"))


class FortiosRangeCheckEligibilityTests(unittest.TestCase):
    """Regression coverage for a real bug: a partial version like "7.2"
    parses successfully to (7, 2), and Python's tuple comparison silently
    allows comparing a 2-tuple against the 3-tuple ranges (e.g.
    (7, 2) < (7, 2, 0) is True) -- which made every range check fail and
    report zero matches, a false "not affected" for a version (7.2.0) that
    IS in range. Range-checking must require exactly MAJOR.MINOR.PATCH."""

    def test_complete_version_is_eligible(self):
        self.assertTrue(fortios_version_ready_for_range_check((7, 2, 0)))

    def test_partial_major_minor_is_not_eligible(self):
        self.assertFalse(fortios_version_ready_for_range_check((7, 2)))

    def test_major_only_is_not_eligible(self):
        self.assertFalse(fortios_version_ready_for_range_check((7,)))

    def test_four_part_version_is_not_eligible(self):
        self.assertFalse(fortios_version_ready_for_range_check((6, 4, 6, 1)))

    def test_none_is_not_eligible(self):
        self.assertFalse(fortios_version_ready_for_range_check(None))


class FortiosCveMatchTests(unittest.TestCase):
    def test_known_affected_version_matches_all_three_cves(self):
        # 6.0.0-6.0.4 is the overlap of all three Fortinet ranges on file.
        matches = fortios_cve_matches((6, 0, 2), FORTINET_ENTRIES)
        self.assertEqual(
            set(matches), {"CVE-2018-13379", "CVE-2022-42475", "CVE-2023-27997"}
        )

    def test_version_just_above_a_fix_no_longer_matches_that_cve(self):
        # 5.4.13 is the documented fixed version for CVE-2018-13379.
        matches = fortios_cve_matches((5, 4, 13), FORTINET_ENTRIES)
        self.assertNotIn("CVE-2018-13379", matches)

    def test_version_in_gap_between_branches_matches_nothing(self):
        # 6.1.0 falls between the 6.0.x and 6.2.x branches on file.
        self.assertEqual(fortios_cve_matches((6, 1, 0), FORTINET_ENTRIES), [])

    def test_partial_version_would_falsely_show_no_match_if_not_guarded(self):
        # Demonstrates *why* the eligibility gate above is required: 7.2.0 is
        # in range for two CVEs, but comparing the partial tuple (7, 2)
        # directly against those same 3-tuple ranges reports zero matches.
        # Callers must check fortios_version_ready_for_range_check() first
        # and refuse to draw a "not affected" conclusion from this shape.
        full = fortios_cve_matches((7, 2, 0), FORTINET_ENTRIES)
        partial = fortios_cve_matches((7, 2), FORTINET_ENTRIES)
        self.assertEqual(set(full), {"CVE-2022-42475", "CVE-2023-27997"})
        self.assertEqual(partial, [])
        self.assertFalse(fortios_version_ready_for_range_check((7, 2)))


if __name__ == "__main__":
    unittest.main()
