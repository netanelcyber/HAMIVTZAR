"""The irrational seed values ``sine_table.py`` builds its table from --
sqrt(2), sqrt(3), sqrt(5), and the two Pythagorean-identity square roots
that turn sin(18) into cos(18) and cos(36) into sin(36) -- traced back to
right triangles via the Pythagorean theorem, and evaluated by inserting
each into the binomial power series for sqrt(1+x), in exact
``fractions.Fraction`` arithmetic. No ``math.sqrt`` anywhere in this file.

Each radical's Pythagorean origin:

  * **sqrt(2)** -- the right triangle with both legs 1: 1^2 + 1^2 = 2.
  * **sqrt(3)** -- bisect an equilateral triangle of side 2. The altitude
    ``h`` and half-base 1 form a right triangle with hypotenuse 2:
    1^2 + h^2 = 2^2, so h = sqrt(3).
  * **sqrt(5)** -- the right triangle with legs 1 and 2: 1^2 + 2^2 = 5.
    (This is the radical behind the golden ratio and so behind
    sin(18)/cos(36), themselves pentagon-construction quantities.)
  * **cos(18) from sin(18), and sin(36) from cos(36)** -- the Pythagorean
    theorem applied directly to the unit circle: for any angle theta,
    sin(theta) and cos(theta) are the legs of a right triangle with
    hypotenuse 1, so cos(theta) = sqrt(1 - sin(theta)^2).

The power series itself: writing a chosen rational ``seed`` close to
sqrt(n), so that ``x = (n - seed^2) / seed^2`` is small, gives
sqrt(n) = seed * sqrt(1 + x), and

    sqrt(1 + x) = sum_{k=0}^{infinity} C(1/2, k) * x^k

(the binomial series for exponent 1/2), which is evaluated here to a fixed
number of terms via the standard recurrence for the generalized binomial
coefficients C(1/2, k). The seeds below are convergents of each radical's
continued fraction, chosen so x is tiny and the truncated series already
agrees with the true value to many more digits than this package needs
anywhere downstream.
"""

from fractions import Fraction


def binomial_sqrt(n: Fraction, seed: Fraction, terms: int = 14) -> Fraction:
    """sqrt(n) via the binomial series for sqrt(1+x), seeded at ``seed``."""
    x = (n - seed * seed) / (seed * seed)
    total = Fraction(0)
    coefficient = Fraction(1)  # C(1/2, 0)
    x_power = Fraction(1)
    for k in range(terms):
        total += coefficient * x_power
        coefficient = coefficient * (Fraction(1, 2) - k) / (k + 1)
        x_power *= x
    return seed * total


# --- Pythagorean-theorem radicals ---
SQRT2 = binomial_sqrt(Fraction(2), Fraction(17, 12))   # 1^2 + 1^2 = 2
SQRT3 = binomial_sqrt(Fraction(3), Fraction(97, 56))   # 1^2 + h^2 = 2^2 (equilateral altitude)
SQRT5 = binomial_sqrt(Fraction(5), Fraction(161, 72))  # 1^2 + 2^2 = 5

# --- Seed angles for the sine table, all exact Fractions ---
SIN30, COS30 = Fraction(1, 2), SQRT3 / 2
SIN60, COS60 = SQRT3 / 2, Fraction(1, 2)
SIN45 = COS45 = SQRT2 / 2
SIN90, COS90 = Fraction(1), Fraction(0)

SIN18 = (SQRT5 - 1) / 4
COS18 = binomial_sqrt(1 - SIN18 * SIN18, Fraction(19, 20))  # Pythagorean identity, unit circle

COS36 = (1 + SQRT5) / 4
SIN36 = binomial_sqrt(1 - COS36 * COS36, Fraction(3, 5))  # Pythagorean identity, unit circle

SIN72, COS72 = COS18, SIN18  # co-function identity, sin(90-x) = cos(x)


def seed_angles_exact():
    """Return {degrees: (sin, cos)} for the constructible seed angles, as
    exact Fractions -- everything sine_table.py needs, with no math.sqrt
    anywhere upstream of it."""
    return {
        18: (SIN18, COS18),
        30: (SIN30, COS30),
        36: (SIN36, COS36),
        45: (SIN45, COS45),
        60: (SIN60, COS60),
        72: (SIN72, COS72),
        90: (SIN90, COS90),
    }
