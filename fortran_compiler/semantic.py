"""Semantic analysis: build symbol tables, resolve ID(args) as array-ref vs.
function-call, propagate expression types, and validate the AST produced by
parser.py before codegen.py runs.

Fortran requires explicit declaration (we always assume IMPLICIT NONE); any
reference to an undeclared/unknown name is an error.
"""

from ast_nodes import (
    Name, ArrayRef, FuncCall, BinOp, UnaryOp,
    IntLit, RealLit, BoolLit, StrLit,
    Assign, Print, ReadStmt, If, DoRange, DoWhile, Call, Return, Stop, Exit, Cycle, NoOp,
)
from intrinsics import is_intrinsic, check_arity, INTRINSICS

NUMERIC = ("integer", "real")


class SemanticError(Exception):
    pass


class Symbol:
    def __init__(self, name, base_type, dims=None, is_param=False):
        self.name = name
        self.type = base_type
        self.dims = dims or []
        self.is_array = bool(dims)
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
        symtab = {}
        for decl in unit.decls:
            for nm in decl.names:
                dims = decl.array_dims.get(nm)
                if nm.lower() in symtab:
                    raise SemanticError(f"'{nm}' redeclared in {unit.name}")
                symtab[nm.lower()] = Symbol(nm, decl.type.base, dims)

        for p in unit.params:
            if p.lower() not in symtab:
                raise SemanticError(f"parameter '{p}' of {unit.name} must be declared")
            symtab[p.lower()].is_param = True

        if unit.kind == "function":
            key = unit.name.lower()
            if key not in symtab:
                symtab[key] = Symbol(unit.name, unit.result_type.base, [])

        info = UnitInfo(unit, symtab)
        self.units_info[unit.name.lower()] = info

        for i, stmt in enumerate(unit.body):
            unit.body[i] = self._check_stmt(stmt, symtab, unit)
        return info

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
            stmt.args = [self._check_expr(a, symtab) for a in stmt.args]
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
            node.index = self._check_expr(node.index, symtab)
            node.type = sym.type
            return node
        raise SemanticError(f"invalid assignment target {type(node).__name__}")

    # ---- expressions ----
    def _check_expr(self, node, symtab):
        if isinstance(node, (IntLit, RealLit, BoolLit, StrLit)):
            return node
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
            node.index = self._check_expr(node.index, symtab)
            node.type = sym.type
            return node
        if isinstance(node, FuncCall):
            key = node.name.lower()
            sym = symtab.get(key)
            if sym is not None and sym.is_array:
                if len(node.args) != 1:
                    raise SemanticError(f"array '{node.name}' requires exactly one index")
                ref = ArrayRef(node.name, self._check_expr(node.args[0], symtab))
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
                node.args = [self._check_expr(a, symtab) for a in node.args]
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
