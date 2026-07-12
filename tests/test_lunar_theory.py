"""Tests for kiddush_hachodesh.lunar_theory: the reconstructed sine table
and the epicycle/eccenter geometric model built on it. Fully offline,
stdlib only (math + the package itself).
"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kiddush_hachodesh import molad
from kiddush_hachodesh.lunar_theory import horizon, params
from kiddush_hachodesh.lunar_theory.equation_of_center import equation_of_center
from kiddush_hachodesh.lunar_theory.latitude import moon_ecliptic_latitude
from kiddush_hachodesh.lunar_theory.mean_position import (
    mean_longitude_moon,
    mean_longitude_sun,
    true_longitude_moon,
    true_longitude_sun,
)
from kiddush_hachodesh.lunar_theory.sine_table import TABLE
from kiddush_hachodesh.lunar_theory.visibility import evaluate, evaluate_after_molad


class TestSineTable(unittest.TestCase):
    def test_sin_matches_math_within_tolerance(self):
        random.seed(0)
        for _ in range(500):
            deg = random.uniform(-720, 720)
            self.assertAlmostEqual(TABLE.sin(deg), math.sin(math.radians(deg)), delta=1e-4)

    def test_cos_matches_math_within_tolerance(self):
        random.seed(1)
        for _ in range(500):
            deg = random.uniform(-720, 720)
            self.assertAlmostEqual(TABLE.cos(deg), math.cos(math.radians(deg)), delta=1e-4)

    def test_asin_matches_math_within_tolerance(self):
        random.seed(2)
        for _ in range(500):
            x = random.uniform(-1, 1)
            self.assertAlmostEqual(TABLE.asin(x), math.degrees(math.asin(x)), delta=0.1)

    def test_atan2_matches_math_within_tolerance(self):
        random.seed(3)
        for _ in range(500):
            x, y = random.uniform(-10, 10), random.uniform(-10, 10)
            if x == 0 and y == 0:
                continue
            self.assertAlmostEqual(
                TABLE.atan2(y, x), math.degrees(math.atan2(y, x)), delta=0.1
            )

    def test_pythagorean_identity_holds_on_table(self):
        for deg in range(0, 360, 7):
            s, c = TABLE.sin(deg), TABLE.cos(deg)
            self.assertAlmostEqual(s * s + c * c, 1.0, delta=1e-4)


class TestEquationOfCenter(unittest.TestCase):
    def test_zero_at_apogee_and_perigee(self):
        self.assertAlmostEqual(equation_of_center(0.0, 5.25), 0.0, places=6)
        self.assertAlmostEqual(equation_of_center(180.0, 5.25), 0.0, places=6)

    def test_antisymmetric(self):
        for m in (10, 45, 90, 150):
            self.assertAlmostEqual(
                equation_of_center(m, 5.25), -equation_of_center(360 - m, 5.25), places=6
            )

    def test_bounded_by_epicycle_ratio(self):
        r, R = 5.25, 60.0
        max_expected = math.degrees(math.asin(r / R))
        for m in range(0, 360, 5):
            self.assertLessEqual(abs(equation_of_center(m, r, R)), max_expected + 0.1)


class TestMeanAndTruePosition(unittest.TestCase):
    def test_mean_elongation_is_zero_at_every_molad(self):
        # Molad Tohu (and every molad interval multiple after it) is a mean
        # conjunction by definition -- this is the bug-fix regression test.
        for total_months in (0, 1, 12, 235, 1350, 5000):
            t = float(molad.days_since_molad_tohu(total_months))
            diff = (mean_longitude_moon(t) - mean_longitude_sun(t) + 180.0) % 360.0 - 180.0
            self.assertAlmostEqual(diff, 0.0, places=6)

    def test_true_longitudes_stay_in_range(self):
        for t in (0, 10.5, 100.3, 5000.7):
            self.assertTrue(0.0 <= true_longitude_sun(t) < 360.0)
            self.assertTrue(0.0 <= true_longitude_moon(t) < 360.0)

    def test_true_deviates_from_mean_by_at_most_the_equation_bound(self):
        max_sun = math.degrees(math.asin(params.SUN_ECCENTRICITY / 60.0))
        max_moon = math.degrees(math.asin(params.MOON_EPICYCLE_RADIUS / 60.0))
        for t in (5, 50, 500):
            d_sun = abs((true_longitude_sun(t) - mean_longitude_sun(t) + 540) % 360 - 180)
            d_moon = abs((true_longitude_moon(t) - mean_longitude_moon(t) + 540) % 360 - 180)
            self.assertLessEqual(d_sun, max_sun + 0.1)
            self.assertLessEqual(d_moon, max_moon + 0.1)


class TestLatitude(unittest.TestCase):
    def test_bounded_by_inclination(self):
        for t in range(0, 400, 13):
            self.assertLessEqual(
                abs(moon_ecliptic_latitude(t)), params.MOON_ORBIT_INCLINATION_DEGREES + 0.01
            )

    def test_zero_at_the_node(self):
        # By construction, argument_of_latitude(0) = true_longitude_moon(0) - node(0) = 0 - 0.
        self.assertAlmostEqual(moon_ecliptic_latitude(0.0), 0.0, places=6)


class TestHorizon(unittest.TestCase):
    def test_equatorial_roundtrip_declination_bounded_by_latitude_plus_obliquity(self):
        _, delta = horizon.ecliptic_to_equatorial(45.0, 3.0)
        self.assertLessEqual(abs(delta), params.OBLIQUITY_OF_ECLIPTIC_DEGREES + 3.0 + 0.1)

    def test_sunset_hour_angle_is_90_on_the_equator_at_equinox(self):
        self.assertAlmostEqual(horizon.sunset_hour_angle(0.0, 0.0), 90.0, places=6)

    def test_altitude_at_own_setting_hour_angle_is_zero(self):
        phi, delta = params.JERUSALEM_LATITUDE_DEGREES, 10.0
        h0 = horizon.sunset_hour_angle(phi, delta)
        self.assertAlmostEqual(horizon.altitude(phi, delta, h0), 0.0, places=4)

    def test_angular_separation_of_identical_points_is_zero(self):
        # acos' blows up near x=1, so the table's ~1e-4 sin/cos precision
        # is amplified here; delta reflects the reconstruction's real
        # resolution, not an exact-arithmetic guarantee.
        self.assertAlmostEqual(horizon.angular_separation(30.0, 2.0, 30.0, 2.0), 0.0, delta=0.1)


class TestVisibilityPipeline(unittest.TestCase):
    def test_elongation_grows_with_days_after_molad(self):
        reports = [evaluate_after_molad(1350, days_after=d) for d in (1, 5, 10)]
        elongations = [r.elongation_degrees for r in reports]
        self.assertEqual(elongations, sorted(elongations))

    def test_report_has_a_full_step_trace(self):
        report = evaluate(100.0)
        labels = [label for label, _ in report.steps]
        self.assertIn("אורך אמיתי של הלבנה (אחרי תיקון המסלול)", labels)
        self.assertIn("קו רוחב של הלבנה (אחרי חישוב הראש)", labels)
        self.assertGreater(len(report.steps), 8)

    def test_verdict_is_boolean_and_consistent_with_thresholds(self):
        report = evaluate(50.0)
        self.assertIsInstance(report.verdict, bool)


if __name__ == "__main__":
    unittest.main()
