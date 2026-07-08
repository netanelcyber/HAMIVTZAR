"""Metadata for supported intrinsic functions, shared by semantic.py (type
propagation) and codegen.py (instruction selection)."""

# ret: 'real' | 'integer' | 'same' (same as arg 1) | 'promote' (real if any arg is real)
# nargs: int (exact) or (min, max) with max=None meaning unbounded
INTRINSICS = {
    "sqrt": {"ret": "real", "nargs": 1},
    "abs":  {"ret": "same", "nargs": 1},
    "mod":  {"ret": "promote", "nargs": 2},
    "int":  {"ret": "integer", "nargs": 1},
    "real": {"ret": "real", "nargs": 1},
    "dble": {"ret": "real", "nargs": 1},
    "max":  {"ret": "promote", "nargs": (2, None)},
    "min":  {"ret": "promote", "nargs": (2, None)},
    "sin":  {"ret": "real", "nargs": 1},
    "cos":  {"ret": "real", "nargs": 1},
    "tan":  {"ret": "real", "nargs": 1},
    "exp":  {"ret": "real", "nargs": 1},
    "log":  {"ret": "real", "nargs": 1},
}


def is_intrinsic(name: str) -> bool:
    return name.lower() in INTRINSICS


def check_arity(name: str, n: int) -> bool:
    spec = INTRINSICS[name.lower()]["nargs"]
    if isinstance(spec, tuple):
        lo, hi = spec
        return n >= lo and (hi is None or n <= hi)
    return n == spec
