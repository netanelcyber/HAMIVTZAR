"""The moon's node ("rosh") and ecliptic latitude ("rochav"), Hilchot
Kiddush HaChodesh ch. 15.

The moon's orbital plane is tilted relative to the ecliptic by a (nearly
constant) inclination ``i``; the line where the two planes cross -- the
line of nodes -- itself slowly regresses. The moon's latitude at any
moment depends only on how far its true longitude has traveled past the
(regressing) node, the "argument of latitude".
"""

from . import params
from .mean_position import true_longitude_moon
from .sine_table import TABLE


def mean_node_longitude(t_days: float) -> float:
    """The ascending node regresses (moves backward through the zodiac)."""
    return (-360.0 * t_days / params.NODAL_MONTH_DAYS) % 360.0


def argument_of_latitude(t_days: float) -> float:
    return (true_longitude_moon(t_days) - mean_node_longitude(t_days)) % 360.0


def moon_ecliptic_latitude(t_days: float) -> float:
    """Signed ecliptic latitude in degrees (positive = north of ecliptic)."""
    u = argument_of_latitude(t_days)
    return TABLE.asin(TABLE.sin(params.MOON_ORBIT_INCLINATION_DEGREES) * TABLE.sin(u))
