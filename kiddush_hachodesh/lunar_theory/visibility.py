"""End-to-end sighting pipeline: from an elapsed-time epoch to a lunar
visibility estimate at a given site, with every intermediate quantity
retained (Hilchot Kiddush HaChodesh chapters 16-18 walk through an
analogous sequence of steps for the evening after the 29th of the month).

The final verdict uses a deliberately simple, explicitly-labeled
illustrative threshold on (elongation, apparent altitude at sunset) -- it
is **not** a reproduction of Rambam's own sighting-criteria table, which
this package does not attempt to transcribe (see the package docstring).
The point of exposing the full trace is that any other threshold can be
applied downstream to the same, real, geometrically-computed numbers.
"""

from dataclasses import dataclass, field

from . import horizon, params
from .latitude import moon_ecliptic_latitude
from .mean_position import (
    mean_anomaly_moon,
    mean_anomaly_sun,
    mean_longitude_moon,
    mean_longitude_sun,
    true_longitude_moon,
    true_longitude_sun,
)

# Illustrative only -- see module docstring.
MIN_ELONGATION_DEGREES = 10.0
MIN_APPARENT_ALTITUDE_DEGREES = 3.0


@dataclass
class SightingReport:
    t_days: float
    site: params.Site
    steps: list = field(default_factory=list)
    elongation_degrees: float = 0.0
    apparent_altitude_degrees: float = 0.0
    verdict: bool = False

    def _add(self, label: str, value):
        self.steps.append((label, value))

    def format(self) -> str:
        lines = [f"חישוב ראיית הירח, t={self.t_days:.6f} ימים מהאפוכה, אתר ({self.site.latitude_degrees:.4f}, {self.site.longitude_degrees:.4f})"]
        for label, value in self.steps:
            if isinstance(value, float):
                lines.append(f"  {label}: {value:.6f}")
            else:
                lines.append(f"  {label}: {value}")
        lines.append(f"  --> אורך קשת (התרחקות): {self.elongation_degrees:.4f}°")
        lines.append(f"  --> גובה נראה של הירח בשקיעה: {self.apparent_altitude_degrees:.4f}°")
        lines.append(f"  --> מסקנה (סף המחשה בלבד, לא טבלת הרמב\"ם המקורית): {'נראה' if self.verdict else 'לא נראה'}")
        return "\n".join(lines)


def evaluate(t_days: float, site: params.Site = params.JERUSALEM) -> SightingReport:
    report = SightingReport(t_days=t_days, site=site)

    lon_sun_mean = mean_longitude_sun(t_days)
    m_sun = mean_anomaly_sun(t_days)
    lon_sun = true_longitude_sun(t_days)
    report._add("אורך ממוצע של החמה", lon_sun_mean)
    report._add("מסלול ממוצע של החמה", m_sun)
    report._add("אורך אמיתי של החמה (אחרי תיקון המסלול)", lon_sun)

    lon_moon_mean = mean_longitude_moon(t_days)
    m_moon = mean_anomaly_moon(t_days)
    lon_moon = true_longitude_moon(t_days)
    report._add("אורך ממוצע של הלבנה", lon_moon_mean)
    report._add("מסלול ממוצע של הלבנה", m_moon)
    report._add("אורך אמיתי של הלבנה (אחרי תיקון המסלול)", lon_moon)

    lat_moon = moon_ecliptic_latitude(t_days)
    report._add("קו רוחב של הלבנה (אחרי חישוב הראש)", lat_moon)

    alpha_sun, delta_sun = horizon.ecliptic_to_equatorial(lon_sun, 0.0)
    alpha_moon, delta_moon = horizon.ecliptic_to_equatorial(lon_moon, lat_moon)
    report._add("עלייה ישרה / נטייה של החמה", (alpha_sun, delta_sun))
    report._add("עלייה ישרה / נטייה של הלבנה", (alpha_moon, delta_moon))

    h0_sun = horizon.sunset_hour_angle(site.latitude_degrees, delta_sun)
    lst_sunset = (alpha_sun + h0_sun) % 360.0
    report._add("זווית שעה של שקיעת החמה", h0_sun)
    report._add("זמן כוכבי מקומי בשקיעה", lst_sunset)

    h_moon = (lst_sunset - alpha_moon) % 360.0
    alt_moon = horizon.altitude(site.latitude_degrees, delta_moon, h_moon)
    report._add("זווית שעה של הלבנה בשקיעת החמה", h_moon)
    report._add("גובה אמיתי של הלבנה", alt_moon)

    alt_moon_apparent = horizon.apparent_altitude(
        alt_moon,
        params.MOON_MEAN_HORIZONTAL_PARALLAX_DEGREES,
        params.STANDARD_REFRACTION_AT_HORIZON_DEGREES,
    )
    report._add("תיקון מקבילית ושבירה", alt_moon_apparent - alt_moon)

    elongation = horizon.angular_separation(lon_sun, 0.0, lon_moon, lat_moon)

    report.elongation_degrees = elongation
    report.apparent_altitude_degrees = alt_moon_apparent
    report.verdict = elongation >= MIN_ELONGATION_DEGREES and alt_moon_apparent >= MIN_APPARENT_ALTITUDE_DEGREES
    return report


def evaluate_after_molad(total_months: int, days_after: float = 1.0, site: params.Site = params.JERUSALEM) -> SightingReport:
    """Convenience wrapper: evaluate the sighting geometry ``days_after``
    days past the molad of ``total_months`` (months elapsed since
    creation), on the Molad-Tohu-anchored time axis ``mean_position.py``
    requires (see ``molad.days_since_molad_tohu``)."""
    from ..molad import days_since_molad_tohu

    t_days = float(days_since_molad_tohu(total_months)) + days_after
    return evaluate(t_days, site)
