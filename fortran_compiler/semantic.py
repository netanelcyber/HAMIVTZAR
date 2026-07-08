"""Semantic analysis: build symbol tables, resolve ID(args) as array-ref vs.
function-call, propagate expression types, and validate the AST produced by
parser.py before codegen.py runs.

Fortran requires explicit declaration (we always assume IMPLICIT NONE); any
reference to an undeclared/unknown name is an error.
"""

from ast_nodes import (
    Name, ArrayRef, WholeArrayRef, ProcRef, FuncCall, BinOp, UnaryOp,
    IntLit, RealLit, BoolLit, StrLit,
    Assign, Print, ReadStmt, If, DoRange, DoWhile, Call, Return, Stop, Exit, Cycle, NoOp,
)
from intrinsics import is_intrinsic, check_arity, INTRINSICS

NUMERIC = ("integer", "real")


class SemanticError(Exception):
    pass


class Symbol:
    def __init__(self, name, base_type, is_param=False, is_external=False, is_bind_c=False):
        self.name = name
        self.type = base_type
        self.dims = []          # list of annotated dim-extent expr nodes; [] if scalar
        self.is_array = False
        self.is_param = is_param
        self.is_external = is_external   # dummy-procedure argument (EXTERNAL)
        self.is_bind_c = is_bind_c       # BIND(C): call the fixed C symbol directly
        self.is_char = False
        self.char_len = 1                # CHARACTER(LEN=n) declared length, compile-time int


# Built-in pseudo-intrinsics (standard Fortran 2003 names) dispatched as
# direct BIND(C) calls to runtime.c. GET_COMMAND_ARGUMENT and
# EXECUTE_COMMAND_LINE need special handling, not just a name rewrite: our
# CHARACTER buffers are fixed-length and space-padded (no null terminator),
# so the C side needs the declared length too, auto-injected here from the
# argument's compile-time-known char_len rather than written by the user.
BUILTIN_CALL_NAMES = {"get_command_argument", "execute_command_line"}
BUILTIN_FUNC_NAMES = {"command_argument_count"}


class UnitInfo:
    """Resolved metadata for one program unit, consumed by codegen."""
    def __init__(self, unit, symtab):
        self.unit = unit
        self.symtab = symtab   # name(lower) -> Symbol


class Analyzer:
    def __init__(self, module):
        self.module = module
        self.procedures = {}   # name(lower) -> ProgramUnit (subroutine/function)
        self.units_info = {}   # unit name(lower) -> UnitInfo
        self.constants = {}    # name(lower) -> (base_type, value); current unit's PARAMETERs

    def analyze(self):
        for unit in self.module.units:
            if unit.kind in ("subroutine", "function"):
                key = unit.name.lower()
                if key in self.procedures:
                    raise SemanticError(f"duplicate procedure definition '{unit.name}'")
                self.procedures[key] = unit

        for unit in self.module.units:
            self._analyze_unit(unit)
        return self.units_info, self.procedures

    def _analyze_unit(self, unit):
        self.constants = {}
        symtab = {}

        # PARAMETER constants first: they're compile-time-only (never get a
        # stack slot) and may be referenced by later declarations' array
        # bounds or initializers, so they must be resolved before anything
        # else. Declaration order matters here (a constant may reference an
        # earlier constant), unlike the ordinary symtab passes below.
        for decl in unit.decls:
            if not decl.is_parameter:
                continue
            for nm in decl.names:
                init_expr = decl.initializers.get(nm)
                if init_expr is None:
                    raise SemanticError(f"PARAMETER '{nm}' must have an initializer")
                if nm.lower() in self.constants:
                    raise SemanticError(f"'{nm}' redeclared in {unit.name}")
                folded_type, val = self._const_eval(init_expr)
                declared = decl.type.base
                if declared == "real" and folded_type != "real":
                    val = float(val)
                elif declared == "integer" and folded_type == "real":
                    val = int(val)
                self.constants[nm.lower()] = (declared, val)

        # Pass 1: register every non-parameter declared name's base type
        # first, so that array-bound expressions in pass 2 (e.g.
        # `INTEGER :: a(n)`, where `n` is another dummy argument declared on
        # a later line) can find every name regardless of declaration order.
        for decl in unit.decls:
            if decl.is_parameter:
                continue
            for nm in decl.names:
                if nm.lower() in symtab or nm.lower() in self.constants:
                    raise SemanticError(f"'{nm}' redeclared in {unit.name}")
                sym = Symbol(nm, decl.type.base, is_external=decl.is_external, is_bind_c=decl.is_bind_c)
                if decl.type.base == "character":
                    sym.is_char = True
                symtab[nm.lower()] = sym

        for p in unit.params:
            if p.lower() not in symtab:
                raise SemanticError(f"parameter '{p}' of {unit.name} must be declared")
            symtab[p.lower()].is_param = True

        # Pass 2: resolve array-bound expressions now that all names (in
        # particular any dummy arguments used as sizes, and any PARAMETER
        # constants) are in scope. CHARACTER lengths are resolved the same
        # way and must always fold to a constant (unlike array bounds,
        # dummy CHARACTER arguments don't get a general assumed-length form
        # in this subset).
        for decl in unit.decls:
            if decl.is_parameter:
                continue
            for nm in decl.names:
                raw_dims = decl.array_dims.get(nm)
                if raw_dims:
                    sym = symtab[nm.lower()]
                    sym.dims = [self._check_expr(d, symtab) for d in raw_dims]
                    sym.is_array = True
                if decl.type.base == "character":
                    sym = symtab[nm.lower()]
                    len_expr = decl.type.char_len if decl.type.char_len is not None else IntLit(1)
                    resolved = self._check_expr(len_expr, symtab)
                    if not isinstance(resolved, IntLit):
                        raise SemanticError(
                            f"CHARACTER length for '{sym.name}' must be a compile-time constant")
                    sym.char_len = resolved.value

        for sym in symtab.values():
            if sym.is_array and not sym.is_param:
                for d in sym.dims:
                    if not isinstance(d, IntLit):
                        raise SemanticError(
                            f"array bound for local array '{sym.name}' must be a "
                            f"constant (only dummy-argument arrays may size "
                            f"themselves from another argument)")

        if unit.kind == "function":
            key = unit.name.lower()
            if key not in symtab:
                symtab[key] = Symbol(unit.name, unit.result_type.base)

        info = UnitInfo(unit, symtab)
        self.units_info[unit.name.lower()] = info

        # Plain (non-PARAMETER) `TYPE :: name = expr` initializers behave as
        # an implicit assignment executed once, at the top of the unit.
        prelude = []
        for decl in unit.decls:
            if decl.is_parameter:
                continue
            for nm in decl.names:
                init_expr = decl.initializers.get(nm)
                if init_expr is not None:
                    prelude.append(Assign(Name(nm), init_expr))
        unit.body = prelude + unit.body

        for i, stmt in enumerate(unit.body):
            unit.body[i] = self._check_stmt(stmt, symtab, unit)
        return info

    def _const_eval(self, node):
        """Fold a compile-time constant expression (PARAMETER initializer or
        an array bound referencing one) down to a (type, value) pair."""
        if isinstance(node, IntLit):
            return ("integer", node.value)
        if isinstance(node, RealLit):
            return ("real", node.value)
        if isinstance(node, BoolLit):
            return ("logical", node.value)
        if isinstance(node, Name):
            key = node.name.lower()
            if key in self.constants:
                return self.constants[key]
            raise SemanticError(f"'{node.name}' is not a compile-time constant")
        if isinstance(node, UnaryOp):
            typ, val = self._const_eval(node.operand)
            if node.op == "-":
                return (typ, -val)
            if node.op == "+":
                return (typ, val)
            if node.op == ".NOT.":
                return ("logical", not val)
            raise SemanticError(f"unsupported constant expression operator '{node.op}'")
        if isinstance(node, BinOp):
            lt, lv = self._const_eval(node.left)
            rt, rv = self._const_eval(node.right)
            rtype = "real" if "real" in (lt, rt) else "integer"
            if node.op == "+":
                result = lv + rv
            elif node.op == "-":
                result = lv - rv
            elif node.op == "*":
                result = lv * rv
            elif node.op == "/":
                if rtype == "integer":
                    result = int(lv / rv) if rv != 0 else 0   # truncate toward zero
                else:
                    result = lv / rv
            elif node.op == "**":
                result = lv ** rv
            else:
                raise SemanticError(f"unsupported constant expression operator '{node.op}'")
            return (rtype, int(result) if rtype == "integer" else float(result))
        raise SemanticError("expression is not a compile-time constant")

    # ---- statements ----
    def _check_stmt(self, stmt, symtab, unit):
        if isinstance(stmt, Assign):
            stmt.target = self._check_lvalue(stmt.target, symtab)
            stmt.value = self._check_expr(stmt.value, symtab)
            if stmt.target.type == "character" and not self._is_valid_char_value(stmt.value):
                raise SemanticError(
                    "CHARACTER assignment only supports a string literal, another "
                    "CHARACTER variable, or '//' concatenation of those in this subset")
            return stmt
        if isinstance(stmt, Print):
            stmt.items = [self._check_expr(e, symtab) for e in stmt.items]
            return stmt
        if isinstance(stmt, ReadStmt):
            stmt.items = [self._check_lvalue(e, symtab) for e in stmt.items]
            return stmt
        if isinstance(stmt, If):
            new_branches = []
            for cond, body in stmt.branches:
                cond2 = self._check_expr(cond, symtab) if cond is not None else None
                body2 = [self._check_stmt(s, symtab, unit) for s in body]
                new_branches.append((cond2, body2))
            stmt.branches = new_branches
            return stmt
        if isinstance(stmt, DoRange):
            sym = symtab.get(stmt.var.lower())
            if sym is None:
                raise SemanticError(f"DO loop variable '{stmt.var}' not declared")
            stmt.start = self._check_expr(stmt.start, symtab)
            stmt.stop = self._check_expr(stmt.stop, symtab)
            if stmt.step is not None:
                stmt.step = self._check_expr(stmt.step, symtab)
            stmt.body = [self._check_stmt(s, symtab, unit) for s in stmt.body]
            return stmt
        if isinstance(stmt, DoWhile):
            stmt.cond = self._check_expr(stmt.cond, symtab)
            stmt.body = [self._check_stmt(s, symtab, unit) for s in stmt.body]
            return stmt
        if isinstance(stmt, Call):
            key = stmt.name.lower()
            if key in BUILTIN_CALL_NAMES:
                return self._check_builtin_call(stmt, symtab)
            sym = symtab.get(key)
            if sym is not None and sym.is_bind_c:
                # Direct call to a fixed runtime.c symbol (by-reference
                # args, like an ordinary Fortran call, but no static
                # signature to check arity against).
                stmt.args = [self._check_call_arg(a, symtab) for a in stmt.args]
                stmt.is_bind_c = True
                return stmt
            if sym is not None and sym.is_external:
                # Indirect call through a dummy-procedure argument: no
                # static signature is known (matches real Fortran without
                # an explicit INTERFACE block), so arity isn't checked.
                stmt.args = [self._check_call_arg(a, symtab) for a in stmt.args]
                stmt.is_indirect = True
                return stmt
            proc = self.procedures.get(stmt.name.lower())
            if proc is None or proc.kind != "subroutine":
                raise SemanticError(f"line {stmt.line}: '{stmt.name}' is not a known SUBROUTINE")
            if len(stmt.args) != len(proc.params):
                raise SemanticError(
                    f"line {stmt.line}: {stmt.name} expects {len(proc.params)} args, got {len(stmt.args)}")
            stmt.args = [self._check_call_arg(a, symtab) for a in stmt.args]
            return stmt
        if isinstance(stmt, (Return, Stop, Exit, Cycle, NoOp)):
            return stmt
        raise SemanticError(f"unhandled statement type {type(stmt).__name__}")

    def _check_lvalue(self, node, symtab):
        if isinstance(node, Name):
            sym = symtab.get(node.name.lower())
            if sym is None:
                raise SemanticError(f"'{node.name}' not declared")
            if sym.is_array:
                raise SemanticError(f"'{node.name}' is an array; an index is required")
            node.type = sym.type
            return node
        if isinstance(node, ArrayRef):
            sym = symtab.get(node.name.lower())
            if sym is None or not sym.is_array:
                raise SemanticError(f"'{node.name}' is not a declared array")
            if len(node.indices) != len(sym.dims):
                raise SemanticError(
                    f"'{node.name}' is declared with {len(sym.dims)} dimension(s), "
                    f"used with {len(node.indices)}")
            node.indices = [self._check_expr(i, symtab) for i in node.indices]
            node.type = sym.type
            return node
        raise SemanticError(f"invalid assignment target {type(node).__name__}")

    def _is_valid_char_value(self, node):
        """A CHARACTER right-hand side supported by this subset: a string
        literal, a CHARACTER variable, or '//' concatenations of those --
        not general CHARACTER-valued expressions (function results, etc.)."""
        if isinstance(node, StrLit):
            return True
        if isinstance(node, Name):
            return node.type == "character"
        if isinstance(node, BinOp) and node.op == "//":
            return self._is_valid_char_value(node.left) and self._is_valid_char_value(node.right)
        return False

    def _char_arg(self, arg, symtab, context):
        """Resolve a CHARACTER-variable actual argument for a builtin that
        needs both its address and its compile-time-known length."""
        if isinstance(arg, Name):
            sym = symtab.get(arg.name.lower())
            if sym is not None and sym.is_char:
                return WholeArrayRef(arg.name, sym.type), sym.char_len
        raise SemanticError(f"{context} requires a CHARACTER variable")

    def _check_builtin_call(self, stmt, symtab):
        key = stmt.name.lower()
        if key == "get_command_argument":
            if len(stmt.args) != 2:
                raise SemanticError("GET_COMMAND_ARGUMENT expects (NUMBER, VALUE)")
            idx = self._check_expr(stmt.args[0], symtab)
            ref, length = self._char_arg(stmt.args[1], symtab,
                                          "GET_COMMAND_ARGUMENT's VALUE argument")
            stmt.args = [idx, ref, IntLit(length)]
            stmt.name = "rt_get_command_argument"
        else:   # execute_command_line
            if len(stmt.args) != 1:
                raise SemanticError("EXECUTE_COMMAND_LINE expects (COMMAND)")
            ref, length = self._char_arg(stmt.args[0], symtab,
                                          "EXECUTE_COMMAND_LINE's COMMAND argument")
            stmt.args = [ref, IntLit(length)]
            stmt.name = "rt_execute_command_line"
        stmt.is_bind_c = True
        return stmt

    def _check_call_arg(self, arg, symtab):
        """Actual arguments to CALL/user functions may be a whole array or
        CHARACTER buffer (passed by reference to its base address, no
        index) or a procedure name -- a known SUBROUTINE/FUNCTION, or an
        EXTERNAL dummy of the *current* unit forwarded further -- in
        addition to ordinary expressions."""
        if isinstance(arg, Name):
            key = arg.name.lower()
            sym = symtab.get(key)
            if sym is not None and sym.is_external:
                return ProcRef(arg.name)
            if sym is None and key in self.procedures:
                return ProcRef(arg.name)
            if sym is not None and (sym.is_array or sym.is_char):
                return WholeArrayRef(arg.name, sym.type)
        return self._check_expr(arg, symtab)

    # ---- expressions ----
    def _check_expr(self, node, symtab):
        if isinstance(node, (IntLit, RealLit, BoolLit, StrLit)):
            return node
        if isinstance(node, Name):
            key = node.name.lower()
            if key in self.constants:
                typ, val = self.constants[key]
                return {"integer": IntLit, "real": RealLit, "logical": BoolLit}[typ](val)
            sym = symtab.get(key)
            if sym is None:
                raise SemanticError(f"'{node.name}' not declared")
            if sym.is_array:
                raise SemanticError(f"'{node.name}' is an array; an index is required")
            node.type = sym.type
            return node
        if isinstance(node, ArrayRef):
            sym = symtab.get(node.name.lower())
            if sym is None or not sym.is_array:
                raise SemanticError(f"'{node.name}' is not a declared array")
            if len(node.indices) != len(sym.dims):
                raise SemanticError(
                    f"'{node.name}' is declared with {len(sym.dims)} dimension(s), "
                    f"used with {len(node.indices)}")
            node.indices = [self._check_expr(i, symtab) for i in node.indices]
            node.type = sym.type
            return node
        if isinstance(node, FuncCall):
            key = node.name.lower()
            if key == "len" and len(node.args) == 1 and isinstance(node.args[0], Name):
                lensym = symtab.get(node.args[0].name.lower())
                if lensym is not None and lensym.is_char:
                    # A compile-time constant for our fixed-length CHARACTER
                    # variables -- no runtime string length concept needed.
                    return IntLit(lensym.char_len)
            if key in BUILTIN_FUNC_NAMES:
                if node.args:
                    raise SemanticError(f"{node.name} takes no arguments")
                node.name = "rt_command_argument_count"
                node.type = "integer"
                node.is_bind_c = True
                return node
            sym = symtab.get(key)
            if sym is not None and sym.is_bind_c:
                node.args = [self._check_call_arg(a, symtab) for a in node.args]
                node.type = sym.type
                node.is_bind_c = True
                return node
            if sym is not None and sym.is_array:
                if len(node.args) != len(sym.dims):
                    raise SemanticError(
                        f"array '{node.name}' is declared with {len(sym.dims)} "
                        f"dimension(s), used with {len(node.args)}")
                ref = ArrayRef(node.name, [self._check_expr(a, symtab) for a in node.args])
                ref.type = sym.type
                return ref
            if sym is not None and sym.is_external:
                # Indirect call through a dummy-procedure argument used as a
                # function (typed EXTERNAL, e.g. `REAL, EXTERNAL :: f`); no
                # static arity check for the same reason as the Call case.
                node.args = [self._check_call_arg(a, symtab) for a in node.args]
                node.type = sym.type
                node.is_indirect = True
                return node
            if is_intrinsic(key):
                node.args = [self._check_expr(a, symtab) for a in node.args]
                if not check_arity(key, len(node.args)):
                    raise SemanticError(f"intrinsic '{key}' called with wrong number of arguments")
                policy = INTRINSICS[key]["ret"]
                if policy == "real":
                    node.type = "real"
                elif policy == "integer":
                    node.type = "integer"
                elif policy == "same":
                    node.type = node.args[0].type
                elif policy == "promote":
                    node.type = "real" if any(a.type == "real" for a in node.args) else "integer"
                return node
            proc = self.procedures.get(key)
            if proc is not None and proc.kind == "function":
                if len(node.args) != len(proc.params):
                    raise SemanticError(
                        f"function '{node.name}' expects {len(proc.params)} args, got {len(node.args)}")
                node.args = [self._check_call_arg(a, symtab) for a in node.args]
                node.type = proc.result_type.base
                return node
            raise SemanticError(f"'{node.name}' is not a declared array, intrinsic, or function")
        if isinstance(node, UnaryOp):
            node.operand = self._check_expr(node.operand, symtab)
            node.type = "logical" if node.op == ".NOT." else node.operand.type
            return node
        if isinstance(node, BinOp):
            node.left = self._check_expr(node.left, symtab)
            node.right = self._check_expr(node.right, symtab)
            if node.op == "//":
                if node.left.type != "character" or node.right.type != "character":
                    raise SemanticError("'//' requires CHARACTER operands on both sides")
                node.type = "character"
            elif node.op in (".AND.", ".OR.", ".EQV.", ".NEQV."):
                node.type = "logical"
            elif node.op in (".EQ.", ".NE.", ".LT.", ".LE.", ".GT.", ".GE.",
                              "==", "/=", "<", "<=", ">", ">="):
                node.type = "logical"
            else:
                node.type = "real" if "real" in (node.left.type, node.right.type) else "integer"
            return node
        raise SemanticError(f"unhandled expression node {type(node).__name__}")


def analyze(module):
    return Analyzer(module).analyze()
