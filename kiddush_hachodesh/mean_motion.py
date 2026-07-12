"""Astronomical constants *derived* from the base halachic constants.

Hilchot Kiddush HaChodesh states two exact facts as integers of chalakim:

  * the mean synodic month ("onat ha-molad"), 6:3
  * the 19-year intercalation cycle of 235 months, 7 of them leap years, 6:11-13

Neither of those two facts is itself a statement about the sun or about
degrees of arc. But together they *imply* a whole family of other
astronomical constants, purely by algebra:

  * the mean tropical (solar) year implied by "235 lunar months = 19 solar
    years"
  * the moon's mean daily motion away from the sun (the elongation rate),
    directly from the length of the synodic month
  * the sun's mean daily motion, from the implied solar year
  * the moon's mean daily motion against the fixed stars, by recombining
    the two above (sidereal rate = synodic/elongation rate + solar rate)

Every function below returns an exact ``Fraction``. Floats appear only in
``compare_to_modern``, where the halachic constant is measured against an
empirically-observed modern value -- which is irrational and can only ever
be approximated, never quoted exactly.
"""

from fractions import Fraction

from .constants import CYCLE_YEARS, MOLAD_INTERVAL_DAYS, MONTHS_PER_CYCLE

DEGREES_PER_CIRCLE = 360

# --- Modern empirical reference values (not from the Rambam; for comparison only) ---
# IAU / observational mean values, in days.
MODERN_MEAN_SYNODIC_MONTH_DAYS = 29.530588853
MODERN_MEAN_TROPICAL_YEAR_DAYS = 365.242190
MODERN_MOON_SIDEREAL_DAILY_DEGREES = 13.176358


def implied_mean_tropical_year_days() -> Fraction:
    """The mean solar year implied by 235 molad-months spanning 19 years.

    This is not stated directly anywhere in the text; it falls out of
    dividing the (exact) length of 235 mean months by 19.
    """
    return Fraction(MONTHS_PER_CYCLE) * MOLAD_INTERVAL_DAYS / CYCLE_YEARS


def moon_sun_daily_elongation_degrees() -> Fraction:
    """Mean daily motion of the moon *away from the sun* (synodic rate).

    A full 360 degrees of elongation is swept out in exactly one molad
    interval, by definition of "synodic month".
    """
    return Fraction(DEGREES_PER_CIRCLE) / MOLAD_INTERVAL_DAYS


def sun_daily_mean_motion_degrees() -> Fraction:
    """Mean daily motion of the sun along the ecliptic.

    A full circle in exactly the implied mean tropical year.
    """
    return Fraction(DEGREES_PER_CIRCLE) / implied_mean_tropical_year_days()


def moon_daily_mean_motion_degrees() -> Fraction:
    """Mean daily motion of the moon against the fixed stars (sidereal rate).

    The moon's motion relative to the sun (elongation rate) plus the sun's
    own motion relative to the stars recovers the moon's motion relative to
    the stars: synodic_rate = sidereal_rate_moon - sidereal_rate_sun.
    """
    return moon_sun_daily_elongation_degrees() + sun_daily_mean_motion_degrees()


def year_length_drift_days() -> Fraction:
    """How much longer the implied mean year is than the true tropical year.

    Positive means the fixed 19-year cycle overshoots the seasons, which is
    the reason the fixed Hebrew calendar drifts against the solar seasons
    over long timescales.
    """
    return implied_mean_tropical_year_days() - Fraction(
        MODERN_MEAN_TROPICAL_YEAR_DAYS
    ).limit_denominator(10**9)


def years_per_day_of_drift() -> Fraction:
    """How many years elapse before the implied year accumulates one full
    day of drift against the true tropical year."""
    drift = year_length_drift_days()
    if drift == 0:
        return Fraction(0)
    return abs(1 / drift)


def compare_to_modern() -> dict:
    """Compare every derived constant above to its modern empirical
    counterpart. Returns exact Fractions alongside their float value and the
    signed error against the modern (float) reference."""

    synodic = MOLAD_INTERVAL_DAYS
    tropical = implied_mean_tropical_year_days()
    elong = moon_sun_daily_elongation_degrees()
    sun_motion = sun_daily_mean_motion_degrees()
    moon_motion = moon_daily_mean_motion_degrees()

    def row(name, exact, modern, unit):
        value = float(exact)
        return {
            "name": name,
            "exact": exact,
            "value": value,
            "modern": modern,
            "error": value - modern,
            "unit": unit,
        }

    return {
        "synodic_month": row(
            "mean synodic month (molad interval)",
            synodic,
            MODERN_MEAN_SYNODIC_MONTH_DAYS,
            "days",
        ),
        "tropical_year": row(
            "implied mean tropical year (19-year cycle)",
            tropical,
            MODERN_MEAN_TROPICAL_YEAR_DAYS,
            "days",
        ),
        "sun_daily_motion": row(
            "sun's mean daily motion",
            sun_motion,
            DEGREES_PER_CIRCLE / MODERN_MEAN_TROPICAL_YEAR_DAYS,
            "deg/day",
        ),
        "moon_daily_motion": row(
            "moon's mean daily motion (sidereal)",
            moon_motion,
            MODERN_MOON_SIDEREAL_DAILY_DEGREES,
            "deg/day",
        ),
        "moon_sun_elongation": row(
            "moon's mean daily elongation from the sun",
            elong,
            DEGREES_PER_CIRCLE / MODERN_MEAN_SYNODIC_MONTH_DAYS,
            "deg/day",
        ),
    }
