"""Exact (rational) astronomical constants derived from Rambam's Hilchot
Kiddush HaChodesh (Mishneh Torah, Sefer Zmanim), chapters 6-10.

Every quantity here is kept as a ``fractions.Fraction`` end to end. The
halachic text itself specifies the core constants as exact integers of
chalakim (parts), so there is no reason to round them to floating point
before deriving the rest. Floats only enter at the very edge, when comparing
a derived constant to a modern empirically-measured value.
"""
