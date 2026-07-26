"""A local, loopback-only rehearsal target for the AC-6/AC-7/OPS-5 controls.

Not a clone of any real product. A generic mock of the *pattern* -- a
patient self-service login using a low-entropy identifier plus a short
secondary code -- so the brute-force/rate-limiting/lockout testing technique
can be practiced against something you run yourself, never against a real
system.
"""
