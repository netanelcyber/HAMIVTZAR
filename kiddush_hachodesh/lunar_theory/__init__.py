"""A geometric (epicycle/eccenter) model of the moon's course, reconstructing
the *method* behind Hilchot Kiddush HaChodesh chapters 11-19: mean motion,
the moon's anomaly correction ("masiloth ha-yareach"), its node and latitude
("rosh", "rochav"), and the horizon/visibility geometry ("re'iyat ha-yareach").

Two separate claims are being made here, and they should not be conflated:

1. The **method** -- an epicyclic/eccentric geometric model evaluated via a
   sexagesimal (base-60) table-and-interpolation trigonometric technique --
   is a faithful reconstruction of how a medieval astronomer working in the
   Ptolemaic/al-Battani tradition (which Rambam's system belongs to) would
   have computed these quantities: not by evaluating a closed-form
   trigonometric function, but by building a table from a handful of
   geometrically-constructible exact angles and then interpolating.
   ``sine_table.py`` implements exactly that construction.

2. The **numeric parameters** fed into that method (epicycle radius, orbital
   inclination, nodal/anomalistic periods, obliquity, parallax) are standard,
   independently-documented values from the history of astronomy -- not
   digits transcribed from the printed tables in Mishneh Torah. Those printed
   table values are not reproduced here because they cannot be reliably
   recalled at digit-level precision without the primary text in hand; see
   ``LUNAR_THEORY.md`` for the full accounting of what is and isn't sourced
   from the halachic text itself versus from general astronomical history.

Consequently, absolute outputs (e.g. "was the moon visible on date X") are
illustrative of the *mechanism*, not a claim to reproduce Rambam's own
tabulated results for any specific historical date.
"""
