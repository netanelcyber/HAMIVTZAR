"""AST node definitions for the Fortran subset.

Plain dataclasses; no behavior. `type` fields on expression nodes are filled
in by the semantic analysis pass (one of 'integer', 'real', 'logical').
"""

from dataclasses import dataclass, field


# ---- types -----------------------------------------------------------------

@dataclass
class TypeSpec:
    base: str                 # 'integer' | 'real' | 'logical' | 'character'
    dims: list = field(default_factory=list)   # list of int sizes, [] if scalar


# ---- top level ---------------------------------------------------------------

@dataclass
class Decl:
    type: TypeSpec
    names: list                # list of str variable names
    array_dims: dict = field(default_factory=dict)   # name -> [dim_expr, ...]; dim_expr is
                                                       # an IntLit for local arrays, or any
                                                       # expression (typically another dummy
                                                       # parameter's Name) for array parameters
    is_parameter: bool = False           # PARAMETER attribute: name(s) are compile-time constants
    initializers: dict = field(default_factory=dict)  # name -> initializer expr ('= expr')


@dataclass
class Param:
    name: str


@dataclass
class ProgramUnit:
    kind: str                  # 'program' | 'subroutine' | 'function'
    name: str
    params: list                # list[str] (subroutine/function only)
    result_type: object         # TypeSpec or None (function only)
    decls: list                  # list[Decl]
    body: list                   # list of statements
    line: int = 0


@dataclass
class Module:
    units: list                # list[ProgramUnit]


# ---- statements --------------------------------------------------------------

@dataclass
class Assign:
    target: object             # Name or ArrayRef
    value: object
    line: int = 0


@dataclass
class Print:
    items: list
    line: int = 0


@dataclass
class ReadStmt:
    items: list                 # list of Name/ArrayRef targets
    line: int = 0


@dataclass
class If:
    branches: list               # list of (cond_expr_or_None, body_list) ; None cond = else
    line: int = 0


@dataclass
class DoRange:
    var: str
    start: object
    stop: object
    step: object                 # expr or None
    body: list
    line: int = 0


@dataclass
class DoWhile:
    cond: object
    body: list
    line: int = 0


@dataclass
class Call:
    name: str
    args: list
    line: int = 0


@dataclass
class Return:
    line: int = 0


@dataclass
class Stop:
    line: int = 0


@dataclass
class Exit:
    line: int = 0


@dataclass
class Cycle:
    line: int = 0


@dataclass
class NoOp:
    line: int = 0


@dataclass
class ExprStmt:
    """A bare CALL-as-statement is represented as Call; this exists for symmetry, unused for now."""
    expr: object
    line: int = 0


# ---- expressions ---------------------------------------------------------------

@dataclass
class IntLit:
    value: int
    type: str = "integer"


@dataclass
class RealLit:
    value: float
    type: str = "real"


@dataclass
class BoolLit:
    value: bool
    type: str = "logical"


@dataclass
class StrLit:
    value: str
    type: str = "character"


@dataclass
class Name:
    name: str
    type: object = None


@dataclass
class ArrayRef:
    name: str
    indices: list
    type: object = None


@dataclass
class WholeArrayRef:
    """A bare array name passed as an actual argument (by reference, whole
    array, no indexing) -- e.g. `CALL sort(a, n)` where `a` is an array."""
    name: str
    type: object = None


@dataclass
class FuncCall:
    name: str
    args: list
    type: object = None


@dataclass
class BinOp:
    op: str
    left: object
    right: object
    type: object = None


@dataclass
class UnaryOp:
    op: str
    operand: object
    type: object = None
