"""Mean and true ecliptic longitude of the sun and moon at an elapsed time
``t`` (days, as a Fraction or float) since Molad Tohu (``t=0``) --
``molad.days_since_molad_tohu`` produces this exact time axis. Molad Tohu
is, by definition, a mean conjunction, so both mean longitudes are pinned
to the same phase (0 degrees) at t=0; this guarantees mean elongation is
exactly zero at every molad, i.e. at every multiple of the molad interval
in t, matching the halachic definition of "molad" (mean sun-moon
conjunction) without introducing any extra assumption.

The **mean longitude** rates for the sun and moon are the exact Fractions
already derived in ``mean_motion.py`` straight from the molad interval and
the 19-year cycle -- no new assumption is introduced there.

The mean **anomaly** (distance from apogee, driving the equation-of-center
correction) and the mean **node** longitude (``latitude.py``) are *not*
derivable from those two halachic facts alone -- they are separate
physical periods. Those periods, and the phase of each quantity at t=0,
come from ``params.py`` and are explicitly documented there as standard
modern values with an arbitrary zero-phase convention, not from the
halachic text. See the package docstring for why.
"""

from .. import mean_motion
from . import params
from .equation_of_center import equation_of_center


def _mod360(x: float) -> float:
    return x % 360.0


def mean_longitude_sun(t_days: float) -> float:
    rate = float(mean_motion.sun_daily_mean_motion_degrees())
    return _mod360(rate * t_days)


def mean_longitude_moon(t_days: float) -> float:
    rate = float(mean_motion.moon_daily_mean_motion_degrees())
    return _mod360(rate * t_days)


def mean_anomaly_sun(t_days: float) -> float:
    return _mod360(360.0 * t_days / params.ANOMALISTIC_YEAR_DAYS)


def mean_anomaly_moon(t_days: float) -> float:
    return _mod360(360.0 * t_days / params.ANOMALISTIC_MONTH_DAYS)


def true_longitude_sun(t_days: float) -> float:
    mean = mean_longitude_sun(t_days)
    correction = equation_of_center(mean_anomaly_sun(t_days), params.SUN_ECCENTRICITY)
    return _mod360(mean + correction)


def true_longitude_moon(t_days: float) -> float:
    mean = mean_longitude_moon(t_days)
    correction = equation_of_center(mean_anomaly_moon(t_days), params.MOON_EPICYCLE_RADIUS)
    return _mod360(mean + correction)
