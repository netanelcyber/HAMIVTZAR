"""Standard, independently-documented astronomical parameters used by the
epicycle/eccenter model in this package.

None of these numbers are transcribed from the printed tables in Mishneh
Torah, Hilchot Kiddush HaChodesh. They are the standard modern (or
long-established historical-astronomy) values for the same physical
quantities Rambam's own tables describe, used here because a faithful
digit-for-digit reproduction of his tables is not attempted (see the
package docstring and ``LUNAR_THEORY.md``). Where a value is essentially
unchanged between antiquity and today (e.g. the sidereal periods of the
moon), that is noted.
"""

from dataclasses import dataclass

# --- Periods (days). Sidereal/anomalistic periods are astronomically
# stable over the relevant timescale, so ancient and modern values agree
# to several significant figures. ---
ANOMALISTIC_MONTH_DAYS = 27.554550  # moon: perigee to perigee
NODAL_MONTH_DAYS = 27.212221        # moon: node to same node (draconic month)
ANOMALISTIC_YEAR_DAYS = 365.259636  # sun: perigee to perigee

# --- Epicycle / eccenter model radii, in the same R=60 units as the sine
# table (sexagesimal convention shared by Ptolemy's chord table and the
# Arabic/Hebrew zij sine tables that descend from it). ---
MOON_EPICYCLE_RADIUS = 5.25   # gives a maximum lunar equation of center of ~5.0 degrees
SUN_ECCENTRICITY = 2.5        # gives a maximum solar equation of center of ~2.4 degrees

# --- Ecliptic geometry ---
OBLIQUITY_OF_ECLIPTIC_DEGREES = 23.4393  # medieval measurements cluster near 23.5 degrees
MOON_ORBIT_INCLINATION_DEGREES = 5.145   # mean inclination to the ecliptic

# --- Parallax / refraction, used only for the moon at low altitude ---
MOON_MEAN_HORIZONTAL_PARALLAX_DEGREES = 0.9508
STANDARD_REFRACTION_AT_HORIZON_DEGREES = 0.5667

# --- Reference site: Jerusalem, the reference locality for sighting in the
# halachic tradition (modern coordinates). ---
JERUSALEM_LATITUDE_DEGREES = 31.7767
JERUSALEM_LONGITUDE_DEGREES = 35.2345


@dataclass(frozen=True)
class Site:
    latitude_degrees: float
    longitude_degrees: float


JERUSALEM = Site(JERUSALEM_LATITUDE_DEGREES, JERUSALEM_LONGITUDE_DEGREES)
