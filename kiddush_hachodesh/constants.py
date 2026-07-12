"""Base constants stated explicitly in Hilchot Kiddush HaChodesh, chapter 6.

All values below are exact integers or exact ``Fraction``s -- nothing here is
a floating-point approximation. This matters because the halachic molad
system *is* an exact rational system (chalakim are integers by definition),
and every "other astronomical constant" we derive from it in
``mean_motion.py`` and ``molad.py`` should stay exact for as long as
algebraically possible, only touching floats when compared against a modern
measured (irrational) value.
"""

from fractions import Fraction

# --- The chelek (part): the halachic unit of time, Hilchot Kiddush HaChodesh 6:2 ---
CHALAKIM_PER_HOUR = 1080
HOURS_PER_DAY = 24
CHALAKIM_PER_DAY = CHALAKIM_PER_HOUR * HOURS_PER_DAY  # 25,920

# --- The molad interval ("onat ha-molad"): the mean synodic month, 6:3 ---
# 29 days, 12 hours, and 793 chalakim.
MOLAD_INTERVAL_DAYS_PART = 29
MOLAD_INTERVAL_HOURS_PART = 12
MOLAD_INTERVAL_CHALAKIM_PART = 793

MOLAD_INTERVAL_CHALAKIM = (
    MOLAD_INTERVAL_DAYS_PART * CHALAKIM_PER_DAY
    + MOLAD_INTERVAL_HOURS_PART * CHALAKIM_PER_HOUR
    + MOLAD_INTERVAL_CHALAKIM_PART
)  # 765,433 chalakim, exactly

MOLAD_INTERVAL_DAYS = Fraction(MOLAD_INTERVAL_CHALAKIM, CHALAKIM_PER_DAY)

# --- Molad Tohu ("BaHaRaD"), the epoch molad the tables are built from, 6:8-10 ---
# Weekday 2 (Monday, 0=Sunday), 5 hours and 204 chalakim into the day.
MOLAD_TOHU_WEEKDAY = 1  # 0=Sunday .. 6=Saturday; Monday = 1
MOLAD_TOHU_HOUR = 5
MOLAD_TOHU_CHALAKIM = 204

MOLAD_TOHU_TOTAL_CHALAKIM = (
    MOLAD_TOHU_WEEKDAY * CHALAKIM_PER_DAY
    + MOLAD_TOHU_HOUR * CHALAKIM_PER_HOUR
    + MOLAD_TOHU_CHALAKIM
)

# --- The 19-year intercalation cycle ("machzor katan"), 6:11-13 ---
CYCLE_YEARS = 19
LEAP_YEARS_IN_CYCLE = frozenset({3, 6, 8, 11, 14, 17, 19})
MONTHS_PER_COMMON_YEAR = 12
MONTHS_PER_LEAP_YEAR = 13

MONTHS_PER_CYCLE = (
    (CYCLE_YEARS - len(LEAP_YEARS_IN_CYCLE)) * MONTHS_PER_COMMON_YEAR
    + len(LEAP_YEARS_IN_CYCLE) * MONTHS_PER_LEAP_YEAR
)  # 235 months
