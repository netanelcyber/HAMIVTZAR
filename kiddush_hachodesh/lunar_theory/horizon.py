"""Spherical astronomy: converting ecliptic longitude/latitude into
equatorial and then horizontal (altitude) coordinates for a given site and
moment, all via the reconstructed sine table. Standard formulas (e.g. Meeus,
*Astronomical Algorithms*, ch. 13); nothing halachic-specific lives here.
"""

from . import params
from .sine_table import TABLE


def ecliptic_to_equatorial(longitude_deg: float, latitude_deg: float, obliquity_deg: float = params.OBLIQUITY_OF_ECLIPTIC_DEGREES):
    """Returns (right_ascension_deg, declination_deg)."""
    lon, lat, eps = longitude_deg, latitude_deg, obliquity_deg

    sin_delta = TABLE.sin(lat) * TABLE.cos(eps) + TABLE.cos(lat) * TABLE.sin(eps) * TABLE.sin(lon)
    delta = TABLE.asin(sin_delta)

    tan_lat = TABLE.sin(lat) / TABLE.cos(lat)
    y = TABLE.sin(lon) * TABLE.cos(eps) - tan_lat * TABLE.sin(eps)
    x = TABLE.cos(lon)
    alpha = TABLE.atan2(y, x) % 360.0

    return alpha, delta


def sunset_hour_angle(latitude_deg: float, declination_deg: float) -> float:
    """The (positive) hour angle, in degrees, at which a body of the given
    declination sets for an observer at the given latitude."""
    tan_phi = TABLE.sin(latitude_deg) / TABLE.cos(latitude_deg)
    tan_delta = TABLE.sin(declination_deg) / TABLE.cos(declination_deg)
    cos_h0 = max(-1.0, min(1.0, -tan_phi * tan_delta))
    return TABLE.acos(cos_h0)


def altitude(latitude_deg: float, declination_deg: float, hour_angle_deg: float) -> float:
    sin_alt = (
        TABLE.sin(declination_deg) * TABLE.sin(latitude_deg)
        + TABLE.cos(declination_deg) * TABLE.cos(latitude_deg) * TABLE.cos(hour_angle_deg)
    )
    return TABLE.asin(max(-1.0, min(1.0, sin_alt)))


def apparent_altitude(true_altitude_deg: float, horizontal_parallax_deg: float, refraction_deg: float) -> float:
    """Parallax lowers the apparent position; refraction raises it."""
    return true_altitude_deg - horizontal_parallax_deg * TABLE.cos(true_altitude_deg) + refraction_deg


def angular_separation(lon1_deg: float, lat1_deg: float, lon2_deg: float, lat2_deg: float) -> float:
    cos_sep = (
        TABLE.sin(lat1_deg) * TABLE.sin(lat2_deg)
        + TABLE.cos(lat1_deg) * TABLE.cos(lat2_deg) * TABLE.cos(lon1_deg - lon2_deg)
    )
    return TABLE.acos(max(-1.0, min(1.0, cos_sep)))
