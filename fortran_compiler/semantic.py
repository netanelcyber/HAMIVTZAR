"""Semantic analysis: build symbol tables, resolve ID(args) as array-ref vs.
function-call, propagate expression types, and validate the AST produced by
parser.py before codegen.py runs.

Fortran requires explicit declaration (we always assume IMPLICIT NONE); any
reference to an undeclared/unknown name is an error.
"""

from ast_nodes import (
    Name, ArrayRef, WholeArrayRef, FuncCall, BinOp, UnaryOp,
    IntLit, RealLit, BoolLit, StrLit,
    Assign, Print, ReadStmt, If, DoRange, DoWhile, Call, Return, Stop, Exit, Cycle, NoOp,
)
from intrinsics import is_intrinsic, check_arity, INTRINSICS

NUMERIC = ("integer", "real")


class SemanticError(Exception):
    pass


class Symbol:
    def __init__(self, name, base_type, is_param=False):
        self.name = name
        self.type = base_type
        self.dims = []          # list of annotated dim-extent expr nodes; [] if scalar
        self.is_array = False
        self.is_param = is_param


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
                symtab[nm.lower()] = Symbol(nm, decl.type.base)

        for p in unit.params:
            if p.lower() not in symtab:
                raise SemanticError(f"parameter '{p}' of {unit.name} must be declared")
            symtab[p.lower()].is_param = True

        # Pass 2: resolve array-bound expressions now that all names (in
        # particular any dummy arguments used as sizes, and any PARAMETER
        # constants) are in scope.
        for decl in unit.decls:
            if decl.is_parameter:
                continue
            for nm in decl.names:
                raw_dims = decl.array_dims.get(nm)
                if raw_dims:
                    sym = symtab[nm.lower()]
                    sym.dims = [self._check_expr(d, symtab) for d in raw_dims]
                    sym.is_array = True

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

    def _check_call_arg(self, arg, symtab):
        """Actual arguments to CALL/user functions may be a whole array
        (passed by reference, no index) in addition to ordinary expressions."""
        if isinstance(arg, Name):
            sym = symtab.get(arg.name.lower())
            if sym is not None and sym.is_array:
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
            sym = symtab.get(key)
            if sym is not None and sym.is_array:
                if len(node.args) != len(sym.dims):
                    raise SemanticError(
                        f"array '{node.name}' is declared with {len(sym.dims)} "
                        f"dimension(s), used with {len(node.args)}")
                ref = ArrayRef(node.name, [self._check_expr(a, symtab) for a in node.args])
                ref.type = sym.type
                return ref
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
            if node.op in (".AND.", ".OR.", ".EQV.", ".NEQV."):
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
