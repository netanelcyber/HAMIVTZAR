"""The epicyclic "equation of center": the correction subtracted from a mean
longitude to get a true longitude, exactly the role Rambam's "masiloth"
correction tables play for the moon (ch. 13) and the analogous solar
correction table plays for the sun (ch. 12).

Model: a body moves uniformly on a small epicycle of radius ``r`` whose
center moves uniformly on a deferent of radius ``R`` (R=60, matching the
sine table). Observed from the deferent's center, the angular offset
between the mean direction (to the epicycle's center) and the true
direction (to the body on the epicycle) is the equation of center. An
eccentric-circle model (used for the sun, classically) produces the same
first-order correction with ``r`` playing the role of the eccentricity
(Apollonius' theorem on the equivalence of eccenter and epicycle models).

All trigonometry here goes through ``sine_table.TABLE`` -- the same
table-and-interpolation technique used throughout this package, not
Python's ``math.sin``/``math.cos``/``math.atan2``.
"""

from .sine_table import RADIUS, TABLE


def equation_of_center(mean_anomaly_degrees: float, epicycle_radius: float, deferent_radius: float = RADIUS) -> float:
    """Signed correction, in degrees, to add to a mean longitude.

    ``mean_anomaly_degrees`` is the body's angular distance from its
    apogee (the direction in which the epicycle bulges "outward"), not
    its longitude.
    """
    m = mean_anomaly_degrees
    opposite = epicycle_radius * TABLE.sin(m)
    adjacent = deferent_radius + epicycle_radius * TABLE.cos(m)
    return TABLE.atan2(opposite, adjacent)
