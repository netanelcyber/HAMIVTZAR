"""Molad calculation by exact integer chelek arithmetic (Hilchot Kiddush
HaChodesh 6:8-13).

Everything here is integer arithmetic in units of chalakim -- there is no
rounding anywhere, since the underlying system (chalakim since Molad Tohu)
is exact by construction. Weekday 0 = Sunday .. 6 = Saturday.
"""

from dataclasses import dataclass

from .constants import (
    CHALAKIM_PER_DAY,
    CHALAKIM_PER_HOUR,
    CYCLE_YEARS,
    LEAP_YEARS_IN_CYCLE,
    MOLAD_INTERVAL_CHALAKIM,
    MOLAD_TOHU_TOTAL_CHALAKIM,
    MONTHS_PER_LEAP_YEAR,
    MONTHS_PER_COMMON_YEAR,
)

_WEEKDAY_NAMES = [
    "ראשון",
    "שני",
    "שלישי",
    "רביעי",
    "חמישי",
    "שישי",
    "שבת",
]


@dataclass(frozen=True)
class Molad:
    total_chalakim: int
    weekday: int
    hour: int
    chalakim: int

    @property
    def weekday_name(self) -> str:
        return _WEEKDAY_NAMES[self.weekday]

    def __str__(self) -> str:
        return f"יום {self.weekday_name}, {self.hour} שעות ו-{self.chalakim} חלקים"


def year_in_cycle(year: int) -> int:
    """1..19 position of ``year`` within its 19-year cycle."""
    if year < 1:
        raise ValueError("year must be >= 1")
    return (year - 1) % CYCLE_YEARS + 1


def is_leap_year(year: int) -> bool:
    return year_in_cycle(year) in LEAP_YEARS_IN_CYCLE


def months_elapsed_before_tishrei(year: int) -> int:
    """Whole molad-months from Molad Tohu to the molad of Tishrei of
    ``year`` (year 1 = the year of creation)."""
    if year < 1:
        raise ValueError("year must be >= 1")

    complete_cycles = (year - 1) // CYCLE_YEARS
    months = complete_cycles * _months_in_full_cycle()

    for y in range(1, year_in_cycle(year)):
        months += MONTHS_PER_LEAP_YEAR if y in LEAP_YEARS_IN_CYCLE else MONTHS_PER_COMMON_YEAR

    return months


def _months_in_full_cycle() -> int:
    return (
        (CYCLE_YEARS - len(LEAP_YEARS_IN_CYCLE)) * MONTHS_PER_COMMON_YEAR
        + len(LEAP_YEARS_IN_CYCLE) * MONTHS_PER_LEAP_YEAR
    )


def molad_from_total_chalakim(total_chalakim: int) -> Molad:
    weekday = (total_chalakim // CHALAKIM_PER_DAY) % 7
    remainder = total_chalakim % CHALAKIM_PER_DAY
    hour = remainder // CHALAKIM_PER_HOUR
    chalakim = remainder % CHALAKIM_PER_HOUR
    return Molad(total_chalakim=total_chalakim, weekday=weekday, hour=hour, chalakim=chalakim)


def molad_tishrei(year: int) -> Molad:
    """Molad of Tishrei (Rosh HaShanah) for the given Hebrew year."""
    months = months_elapsed_before_tishrei(year)
    total_chalakim = MOLAD_TOHU_TOTAL_CHALAKIM + months * MOLAD_INTERVAL_CHALAKIM
    return molad_from_total_chalakim(total_chalakim)
