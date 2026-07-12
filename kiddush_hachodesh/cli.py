"""CLI: python -m kiddush_hachodesh.cli <constants|drift|molad YEAR>"""

import argparse
import sys
from fractions import Fraction

from . import constants as C
from . import mean_motion as MM
from .molad import is_leap_year, molad_tishrei


def _fmt_deg(f: Fraction) -> str:
    whole = int(f)
    minutes_f = (f - whole) * 60
    minutes = int(minutes_f)
    seconds = (minutes_f - minutes) * 60
    return f"{whole}°{minutes}'{float(seconds):.2f}\" ({float(f):.10f}°)"


def cmd_constants(_args) -> None:
    print("קבועי-יסוד (הלכות קידוש החודש, פרק ו) -- מדויקים, ללא עיגול:")
    print(f"  חלק = 1/{C.CHALAKIM_PER_HOUR} שעה; יממה = {C.CHALAKIM_PER_DAY} חלקים")
    print(
        "  עונת המולד (חודש סינודי ממוצע) = "
        f"{C.MOLAD_INTERVAL_DAYS_PART}ד {C.MOLAD_INTERVAL_HOURS_PART}ש "
        f"{C.MOLAD_INTERVAL_CHALAKIM_PART}ח = {C.MOLAD_INTERVAL_CHALAKIM} חלקים "
        f"= {C.MOLAD_INTERVAL_DAYS} ימים ({float(C.MOLAD_INTERVAL_DAYS):.10f})"
    )
    print(
        f"  מולד תוהו = יום {C.MOLAD_TOHU_WEEKDAY} (ב'), "
        f"{C.MOLAD_TOHU_HOUR} שעות, {C.MOLAD_TOHU_CHALAKIM} חלקים"
    )
    print(
        f"  מחזור {C.CYCLE_YEARS} שנה = {C.MONTHS_PER_CYCLE} חודשים, "
        f"שנים מעוברות: {sorted(C.LEAP_YEARS_IN_CYCLE)}"
    )
    print()
    print("קבועים אסטרונומיים נגזרים (חישוב אלגברי מדויק מהנתונים לעיל):")
    tropical = MM.implied_mean_tropical_year_days()
    print(f"  שנת חמה משתמעת (235 חודשים / 19 שנה) = {tropical} ימים ({float(tropical):.10f})")
    print(f"  מהלך יומי ממוצע של החמה = {_fmt_deg(MM.sun_daily_mean_motion_degrees())}")
    print(f"  מהלך יומי ממוצע של הלבנה (ביחס לכוכבים) = {_fmt_deg(MM.moon_daily_mean_motion_degrees())}")
    print(f"  התרחקות יומית ממוצעת של הלבנה מהחמה = {_fmt_deg(MM.moon_sun_daily_elongation_degrees())}")


def cmd_drift(_args) -> None:
    comparison = MM.compare_to_modern()
    print("השוואה לערכים אסטרונומיים מודרניים (נמדדים, לא הלכתיים):")
    for row in comparison.values():
        print(
            f"  {row['name']}: {row['value']:.10f} {row['unit']} "
            f"(מודרני: {row['modern']:.10f}, סטייה: {row['error']:+.2e})"
        )
    drift = MM.year_length_drift_days()
    ypd = MM.years_per_day_of_drift()
    print()
    print(
        f"שנת ה-19 המשתמעת ארוכה מהשנה הטרופית האמיתית ב-{float(drift):.6f} יום/שנה "
        f"-> סטייה של יום שלם כל כ-{float(ypd):.1f} שנה."
    )


def cmd_molad(args) -> None:
    m = molad_tishrei(args.year)
    leap = "כן" if is_leap_year(args.year) else "לא"
    print(f"מולד תשרי לשנה {args.year}: {m}  (שנה מעוברת: {leap})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="kiddush_hachodesh")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("constants", help="Print base + derived constants").set_defaults(func=cmd_constants)
    sub.add_parser("drift", help="Compare derived constants to modern values").set_defaults(func=cmd_drift)

    p_molad = sub.add_parser("molad", help="Compute the molad of Tishrei for a given Hebrew year")
    p_molad.add_argument("year", type=int)
    p_molad.set_defaults(func=cmd_molad)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
