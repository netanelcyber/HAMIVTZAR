"""A reconstructed sexagesimal (R=60) sine table, built and consulted the
way a medieval zij (astronomical handbook) -- the tradition Rambam's
Hilchot Kiddush HaChodesh chapters 11-19 draw on -- would actually have
built and used one: not a closed-form trigonometric function, but a table
of values at a fixed angular step, filled in by geometric construction and
consulted by linear interpolation ("taking the proportional part", the
technique Rambam himself repeatedly invokes when reading his own tables).

Construction, in three stages that mirror the historical technique
(compare Ptolemy, *Almagest* I.10-11):

1. **Exact seed angles.** A handful of angles are constructible with
   compass and straightedge, so their sine/cosine are exact algebraic
   (radical) expressions: 18, 30, 36, 45, 60, 72, 90 degrees.
2. **Combine and bisect.** The angle-difference identity gives an exact
   value at 72-60 = 12 degrees. Repeated half-angle bisection then drives
   this down to a small base step (here 0.1875 degrees, i.e. 12 / 2**6).
3. **Step out the full table.** Starting from sin(0)=0, cos(0)=1, the
   angle-addition identity is applied repeatedly to advance by the base
   step until 90 degrees is covered. This is the same "walk the table
   forward one row at a time" construction a zij's author would have used.

Lookups for arbitrary angles, and their inverses (asin/atan2), use linear
interpolation between the two bracketing table rows -- again, table lookup
plus a proportional part, not a call to a black-box trig function.
"""

import math
from dataclasses import dataclass

RADIUS = 60.0
BASE_STEP_DEGREES = 12.0 / (2 ** 6)  # 0.1875 degrees


def _exact_seed_angles():
    """Sine/cosine of the constructible seed angles, from closed-form
    radical expressions -- not from math.sin/cos."""
    sin18 = (math.sqrt(5) - 1) / 4
    cos18 = math.sqrt(1 - sin18 ** 2)
    sin30, cos30 = 0.5, math.sqrt(3) / 2
    sin36 = math.sqrt(10 - 2 * math.sqrt(5)) / 4
    cos36 = (1 + math.sqrt(5)) / 4
    sin45 = cos45 = math.sqrt(2) / 2
    sin60, cos60 = cos30, sin30
    sin72, cos72 = cos18, sin18
    sin90, cos90 = 1.0, 0.0
    return {
        18: (sin18, cos18),
        30: (sin30, cos30),
        36: (sin36, cos36),
        45: (sin45, cos45),
        60: (sin60, cos60),
        72: (sin72, cos72),
        90: (sin90, cos90),
    }


def _angle_difference(sin_a, cos_a, sin_b, cos_b):
    """sin/cos(A - B) from sin/cos(A), sin/cos(B) -- the chord-subtraction
    identity, in modern notation."""
    return sin_a * cos_b - cos_a * sin_b, cos_a * cos_b + sin_a * sin_b


def _angle_sum(sin_a, cos_a, sin_b, cos_b):
    """sin/cos(A + B) -- the chord-addition identity."""
    return sin_a * cos_b + cos_a * sin_b, cos_a * cos_b - sin_a * sin_b


def _half_angle(sin_a, cos_a):
    """sin/cos(A / 2) from sin/cos(A), for A in [0, 180] (positive root)."""
    return math.sqrt((1 - cos_a) / 2), math.sqrt((1 + cos_a) / 2)


def _build_table():
    seeds = _exact_seed_angles()
    sin12, cos12 = _angle_difference(*seeds[72], *seeds[60])

    s, c, angle = sin12, cos12, 12.0
    while angle > BASE_STEP_DEGREES * 1.0001:
        s, c = _half_angle(s, c)
        angle /= 2

    steps = round(90.0 / BASE_STEP_DEGREES)
    rows = [(0.0, 0.0, 1.0)]
    cs, cc = 0.0, 1.0
    for k in range(1, steps + 1):
        cs, cc = _angle_sum(cs, cc, s, c)
        rows.append((k * BASE_STEP_DEGREES, cs, cc))
    return rows


_TABLE = _build_table()  # rows of (degrees, sin, cos), 0..90 by BASE_STEP_DEGREES


@dataclass(frozen=True)
class SineTable:
    """Table-lookup trigonometry with R=60, as a zij would tabulate it."""

    def _bracket(self, deg_0_90: float):
        idx = deg_0_90 / BASE_STEP_DEGREES
        i0 = int(idx)
        i0 = max(0, min(i0, len(_TABLE) - 1))
        i1 = min(i0 + 1, len(_TABLE) - 1)
        frac = idx - i0
        return _TABLE[i0], _TABLE[i1], frac

    def sin(self, degrees: float) -> float:
        d = degrees % 360.0
        sign = 1.0
        if d > 180.0:
            d -= 180.0
            sign = -1.0
        if d > 90.0:
            d = 180.0 - d
        row0, row1, frac = self._bracket(d)
        s0, s1 = row0[1], row1[1]
        return sign * (s0 + (s1 - s0) * frac)

    def cos(self, degrees: float) -> float:
        return self.sin(degrees + 90.0)

    def rsin(self, degrees: float) -> float:
        """The tabulated quantity itself: R*sin(theta), R=60."""
        return RADIUS * self.sin(degrees)

    def asin(self, x: float) -> float:
        """Inverse lookup: search the table for the bracketing rows whose
        sine values straddle x, then interpolate the angle."""
        sign = 1.0
        if x < 0:
            sign, x = -1.0, -x
        x = min(x, 1.0)
        lo, hi = 0, len(_TABLE) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if _TABLE[mid][1] <= x:
                lo = mid
            else:
                hi = mid
        a0, s0, _ = _TABLE[lo]
        a1, s1, _ = _TABLE[hi]
        frac = 0.0 if s1 == s0 else (x - s0) / (s1 - s0)
        return sign * (a0 + (a1 - a0) * frac)

    def acos(self, x: float) -> float:
        return 90.0 - self.asin(x)

    def atan2(self, y: float, x: float) -> float:
        """Angle of (x, y) in degrees, in (-180, 180], via asin of the
        normalized ordinate plus quadrant correction -- same convention as
        ``math.atan2``."""
        r = math.hypot(x, y)
        if r == 0.0:
            return 0.0
        angle = self.asin(y / r)
        if x < 0:
            angle = (180.0 - angle) if y >= 0 else (-180.0 - angle)
        return angle


TABLE = SineTable()
