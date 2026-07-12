"""Tests for kiddush_hachodesh: exact-arithmetic astronomical constants
derived from Hilchot Kiddush HaChodesh. Fully offline, stdlib only.
"""

import os
import sys
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kiddush_hachodesh import constants as C
from kiddush_hachodesh import mean_motion as MM
from kiddush_hachodesh.molad import (
    is_leap_year,
    molad_tishrei,
    months_elapsed_before_tishrei,
    year_in_cycle,
)


class TestBaseConstants(unittest.TestCase):
    def test_chelek_units(self):
        self.assertEqual(C.CHALAKIM_PER_DAY, 25920)

    def test_molad_interval_exact_chalakim(self):
        # 29d 12h 793p in chalakim, the number classically quoted for the
        # mean synodic month in the fixed Hebrew calendar.
        self.assertEqual(C.MOLAD_INTERVAL_CHALAKIM, 765433)

    def test_molad_interval_as_fraction(self):
        expected = Fraction(29) + Fraction(1, 2) + Fraction(793, 25920)
        self.assertEqual(C.MOLAD_INTERVAL_DAYS, expected)

    def test_molad_interval_close_to_modern_synodic_month(self):
        # The famous near-half-second accuracy of the Rabbinic value.
        diff_seconds = abs(float(C.MOLAD_INTERVAL_DAYS) - 29.530588853) * 86400
        self.assertLess(diff_seconds, 1.0)

    def test_cycle_structure(self):
        self.assertEqual(len(C.LEAP_YEARS_IN_CYCLE), 7)
        self.assertEqual(C.MONTHS_PER_CYCLE, 235)
        self.assertEqual(C.LEAP_YEARS_IN_CYCLE, frozenset({3, 6, 8, 11, 14, 17, 19}))


class TestMeanMotion(unittest.TestCase):
    def test_implied_tropical_year_matches_known_hebrew_calendar_value(self):
        year = MM.implied_mean_tropical_year_days()
        # The well-known ~365.2468-day mean year of the fixed calendar.
        self.assertAlmostEqual(float(year), 365.2468, places=4)

    def test_all_derived_values_are_exact_fractions(self):
        for value in (
            MM.implied_mean_tropical_year_days(),
            MM.moon_sun_daily_elongation_degrees(),
            MM.sun_daily_mean_motion_degrees(),
            MM.moon_daily_mean_motion_degrees(),
        ):
            self.assertIsInstance(value, Fraction)

    def test_sidereal_identity_synodic_equals_sidereal_moon_minus_sidereal_sun(self):
        # Exact algebraic identity, not an approximation: this must hold
        # to the last chelek since moon_daily_motion is defined as
        # elongation + sun_motion.
        elong = MM.moon_sun_daily_elongation_degrees()
        sun = MM.sun_daily_mean_motion_degrees()
        moon = MM.moon_daily_mean_motion_degrees()
        self.assertEqual(moon - sun, elong)

    def test_moon_daily_motion_close_to_modern_value(self):
        moon = float(MM.moon_daily_mean_motion_degrees())
        self.assertAlmostEqual(moon, MM.MODERN_MOON_SIDEREAL_DAILY_DEGREES, places=1)

    def test_drift_is_positive_and_around_two_centuries_per_day(self):
        years_per_day = float(MM.years_per_day_of_drift())
        self.assertGreater(years_per_day, 150)
        self.assertLess(years_per_day, 300)

    def test_compare_to_modern_has_all_rows(self):
        rows = MM.compare_to_modern()
        self.assertEqual(
            set(rows),
            {
                "synodic_month",
                "tropical_year",
                "sun_daily_motion",
                "moon_daily_motion",
                "moon_sun_elongation",
            },
        )
        for row in rows.values():
            self.assertIsInstance(row["exact"], Fraction)
            self.assertIsInstance(row["value"], float)


class TestMolad(unittest.TestCase):
    def test_molad_tohu_is_year_one(self):
        m = molad_tishrei(1)
        self.assertEqual(m.weekday, C.MOLAD_TOHU_WEEKDAY)
        self.assertEqual(m.hour, C.MOLAD_TOHU_HOUR)
        self.assertEqual(m.chalakim, C.MOLAD_TOHU_CHALAKIM)

    def test_year_in_cycle_wraps(self):
        self.assertEqual(year_in_cycle(1), 1)
        self.assertEqual(year_in_cycle(19), 19)
        self.assertEqual(year_in_cycle(20), 1)
        self.assertEqual(year_in_cycle(38), 19)

    def test_leap_years_match_cycle_pattern(self):
        for y in range(1, 20):
            self.assertEqual(is_leap_year(y), y in {3, 6, 8, 11, 14, 17, 19})

    def test_months_elapsed_monotonic(self):
        prev = months_elapsed_before_tishrei(1)
        for year in range(2, 60):
            cur = months_elapsed_before_tishrei(year)
            self.assertGreater(cur, prev)
            prev = cur

    def test_full_cycle_adds_235_months(self):
        self.assertEqual(
            months_elapsed_before_tishrei(20) - months_elapsed_before_tishrei(1),
            235,
        )

    def test_molad_advances_by_one_interval_per_month(self):
        m1 = molad_tishrei(2)
        m2 = molad_tishrei(3)
        months_between = months_elapsed_before_tishrei(3) - months_elapsed_before_tishrei(2)
        expected_chalakim = m1.total_chalakim + months_between * C.MOLAD_INTERVAL_CHALAKIM
        self.assertEqual(m2.total_chalakim, expected_chalakim)


if __name__ == "__main__":
    unittest.main()
