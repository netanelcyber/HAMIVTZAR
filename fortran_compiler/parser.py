"""Recursive-descent parser: token stream (lexer.py) -> AST (ast_nodes.py).

Grammar is documented alongside each parse_* method. Statement labels and
GOTO are intentionally unsupported (no examples in this project's subset use
them); structured control flow (IF/THEN/ELSE, DO, DO WHILE, EXIT/CYCLE)
covers everything the examples need.
"""

from ast_nodes import (
    TypeSpec, Decl, ProgramUnit, Module,
    Assign, Print, ReadStmt, If, DoRange, DoWhile, Call, Return, Stop, Exit, Cycle, NoOp,
    IntLit, RealLit, BoolLit, StrLit, Name, ArrayRef, FuncCall, BinOp, UnaryOp,
)

TYPE_KEYWORDS = {"INTEGER", "REAL", "LOGICAL", "CHARACTER", "DOUBLE"}
REL_OPS = {".EQ.", ".NE.", ".LT.", ".LE.", ".GT.", ".GE.", "==", "/=", "<", "<=", ">", ">="}
END_UNIT_KEYWORDS = {"END"}
BLOCK_TERMINATORS = {"END", "ELSE", "ENDIF", "ENDDO", "EOF"}


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens):
        self.toks = tokens
        self.pos = 0

    # --- token helpers ---
    def cur(self):
        return self.toks[self.pos]

    def kind(self):
        return self.toks[self.pos].kind

    def advance(self):
        t = self.toks[self.pos]
        self.pos += 1
        return t

    def check(self, kind):
        return self.kind() == kind

    def accept(self, kind):
        if self.check(kind):
            return self.advance()
        return None

    def expect(self, kind):
        if not self.check(kind):
            t = self.cur()
            raise ParseError(f"line {t.line}: expected {kind!r}, got {t.kind!r} ({t.value!r})")
        return self.advance()

    def skip_newlines(self):
        while self.check("NEWLINE"):
            self.advance()

    # --- top level ---
    def parse_module(self):
        units = []
        self.skip_newlines()
        while not self.check("EOF"):
            units.append(self.parse_unit())
            self.skip_newlines()
        return Module(units)

    def parse_unit(self):
        result_type = None
        if self.kind() in TYPE_KEYWORDS:
            result_type = self.parse_type_spec()
        if self.check("PROGRAM"):
            self.advance()
            name = self.expect("ID").value
            self.expect("NEWLINE")
            decls, body = self.parse_decls_and_body()
            self.expect_end("PROGRAM", name)
            return ProgramUnit("program", name, [], None, decls, body)
        if self.check("SUBROUTINE"):
            line = self.cur().line
            self.advance()
            name = self.expect("ID").value
            params = self.parse_param_list()
            self.expect("NEWLINE")
            decls, body = self.parse_decls_and_body()
            self.expect_end("SUBROUTINE", name)
            return ProgramUnit("subroutine", name, params, None, decls, body, line)
        if self.check("FUNCTION"):
            line = self.cur().line
            self.advance()
            name = self.expect("ID").value
            params = self.parse_param_list()
            self.expect("NEWLINE")
            decls, body = self.parse_decls_and_body()
            self.expect_end("FUNCTION", name)
            if result_type is None:
                result_type = TypeSpec("real", [])
                for d in decls:
                    if name in d.names:
                        result_type = d.type
                        break
            return ProgramUnit("function", name, params, result_type, decls, body, line)
        t = self.cur()
        raise ParseError(f"line {t.line}: expected PROGRAM/SUBROUTINE/FUNCTION, got {t.kind!r}")

    def expect_end(self, unit_kw, name):
        self.expect("END")
        if self.check(unit_kw):
            self.advance()
            if self.check("ID"):
                self.advance()
        self.skip_newlines_or_eof()

    def skip_newlines_or_eof(self):
        if self.check("NEWLINE"):
            self.advance()
        elif self.check("EOF"):
            pass

    def parse_param_list(self):
        self.expect("(")
        params = []
        if not self.check(")"):
            params.append(self.expect("ID").value)
            while self.accept(","):
                params.append(self.expect("ID").value)
        self.expect(")")
        return params

    def parse_type_spec(self):
        if self.check("DOUBLE"):
            self.advance()
            if self.check("PRECISION"):
                self.advance()
            base = "real"
        else:
            base = self.advance().kind.lower()
            if base == "character" and self.check("("):
                # CHARACTER(LEN=n) -- consume and ignore length spec
                depth = 0
                while True:
                    t = self.advance()
                    if t.kind == "(":
                        depth += 1
                    elif t.kind == ")":
                        depth -= 1
                        if depth == 0:
                            break
        return TypeSpec(base, [])

    # --- declarations & body ---
    def parse_decls_and_body(self):
        decls = []
        while self.kind() in TYPE_KEYWORDS or self.check("IMPLICIT") or self.check("PARAMETER"):
            if self.check("IMPLICIT"):
                self.advance()
                if self.check("NONE"):
                    self.advance()
                self.expect("NEWLINE")
                continue
            if self.check("PARAMETER"):
                t = self.cur()
                raise ParseError(
                    f"line {t.line}: standalone PARAMETER (name = value, ...) statements are "
                    f"not supported; declare the constant with its type instead, e.g. "
                    f"'INTEGER, PARAMETER :: name = value'")
            decls.append(self.parse_decl())
        body = self.parse_stmt_list()
        return decls, body

    ATTR_KEYWORDS = ("PARAMETER", "INTENT", "DIMENSION")

    def parse_decl(self):
        typ = self.parse_type_spec()
        is_parameter = False
        default_dims = None
        while self.check(",") and self.toks[self.pos + 1].kind in self.ATTR_KEYWORDS:
            self.advance()  # ','
            attr = self.advance()
            if attr.kind == "PARAMETER":
                is_parameter = True
            elif attr.kind == "INTENT":
                self.expect("(")
                self.advance()          # IN / OUT / INOUT
                self.expect(")")
            elif attr.kind == "DIMENSION":
                self.expect("(")
                default_dims = [self.parse_expr()]
                while self.accept(","):
                    default_dims.append(self.parse_expr())
                self.expect(")")
        self.accept("::")
        names = []
        array_dims = {}
        initializers = {}
        while True:
            name = self.expect("ID").value
            if self.accept("("):
                # Bound may be a literal (local array) or an expression
                # referencing another dummy argument (array parameter,
                # e.g. `INTEGER :: a(n)`); semantic.py enforces that local
                # (non-parameter) array bounds fold to a constant.
                dims = [self.parse_expr()]
                while self.accept(","):
                    dims.append(self.parse_expr())
                self.expect(")")
                array_dims[name] = dims
            elif default_dims is not None:
                array_dims[name] = list(default_dims)
            if self.accept("="):
                initializers[name] = self.parse_expr()
            names.append(name)
            if not self.accept(","):
                break
        self.expect("NEWLINE")
        return Decl(typ, names, array_dims, is_parameter, initializers)

    # --- statements ---
    def parse_stmt_list(self):
        stmts = []
        self.skip_newlines()
        while self.kind() not in BLOCK_TERMINATORS:
            stmts.append(self.parse_stmt())
            self.skip_newlines()
        return stmts

    def parse_stmt(self):
        k = self.kind()
        line = self.cur().line
        if k == "ID":
            return self.parse_assign()
        if k == "PRINT":
            return self.parse_print()
        if k == "WRITE":
            return self.parse_write()
        if k == "READ":
            return self.parse_read()
        if k == "IF":
            return self.parse_if()
        if k == "DO":
            return self.parse_do()
        if k == "CALL":
            return self.parse_call_stmt()
        if k == "RETURN":
            self.advance()
            self.expect("NEWLINE")
            return Return(line)
        if k == "STOP":
            self.advance()
            if self.check("STR") or self.check("INT"):
                self.advance()
            self.expect("NEWLINE")
            return Stop(line)
        if k == "EXIT":
            self.advance()
            self.expect("NEWLINE")
            return Exit(line)
        if k == "CYCLE":
            self.advance()
            self.expect("NEWLINE")
            return Cycle(line)
        if k == "CONTINUE":
            self.advance()
            self.expect("NEWLINE")
            return NoOp(line)
        t = self.cur()
        raise ParseError(f"line {t.line}: unexpected token {t.kind!r} at start of statement")

    def parse_assign(self):
        line = self.cur().line
        name = self.expect("ID").value
        if self.accept("("):
            indices = [self.parse_expr()]
            while self.accept(","):
                indices.append(self.parse_expr())
            self.expect(")")
            target = ArrayRef(name, indices)
        else:
            target = Name(name)
        self.expect("=")
        value = self.parse_expr()
        self.expect("NEWLINE")
        return Assign(target, value, line)

    def parse_print(self):
        line = self.cur().line
        self.expect("PRINT")
        self.expect("*")
        items = []
        if self.accept(","):
            items.append(self.parse_expr())
            while self.accept(","):
                items.append(self.parse_expr())
        self.expect("NEWLINE")
        return Print(items, line)

    def parse_write(self):
        line = self.cur().line
        self.expect("WRITE")
        self.expect("(")
        self.expect("*")
        self.expect(",")
        self.expect("*")
        self.expect(")")
        items = []
        if not self.check("NEWLINE"):
            items.append(self.parse_expr())
            while self.accept(","):
                items.append(self.parse_expr())
        self.expect("NEWLINE")
        return Print(items, line)

    def parse_read(self):
        line = self.cur().line
        self.expect("READ")
        if self.check("*"):
            self.advance()
            self.expect(",")
        else:
            self.expect("(")
            self.expect("*")
            self.expect(",")
            self.expect("*")
            self.expect(")")
        items = [self.parse_lvalue()]
        while self.accept(","):
            items.append(self.parse_lvalue())
        self.expect("NEWLINE")
        return ReadStmt(items, line)

    def parse_lvalue(self):
        name = self.expect("ID").value
        if self.accept("("):
            indices = [self.parse_expr()]
            while self.accept(","):
                indices.append(self.parse_expr())
            self.expect(")")
            return ArrayRef(name, indices)
        return Name(name)

    def parse_if(self):
        line = self.cur().line
        self.expect("IF")
        self.expect("(")
        cond = self.parse_expr()
        self.expect(")")
        if self.check("THEN"):
            self.advance()
            self.expect("NEWLINE")
            branches = []
            body = self.parse_stmt_list()
            branches.append((cond, body))
            while self.check("ELSE"):
                self.advance()
                if self.check("IF"):
                    self.advance()
                    self.expect("(")
                    c2 = self.parse_expr()
                    self.expect(")")
                    self.expect("THEN")
                    self.expect("NEWLINE")
                    b2 = self.parse_stmt_list()
                    branches.append((c2, b2))
                else:
                    self.expect("NEWLINE")
                    b_else = self.parse_stmt_list()
                    branches.append((None, b_else))
                    break
            if self.check("ENDIF"):
                self.advance()
            else:
                self.expect("END")
                self.expect("IF")
            self.expect("NEWLINE")
            return If(branches, line)
        else:
            # single-line IF (cond) stmt
            stmt = self.parse_stmt()
            return If([(cond, [stmt])], line)

    def parse_do(self):
        line = self.cur().line
        self.expect("DO")
        if self.check("WHILE"):
            self.advance()
            self.expect("(")
            cond = self.parse_expr()
            self.expect(")")
            self.expect("NEWLINE")
            body = self.parse_stmt_list()
            self._expect_enddo()
            return DoWhile(cond, body, line)
        var = self.expect("ID").value
        self.expect("=")
        start = self.parse_expr()
        self.expect(",")
        stop = self.parse_expr()
        step = None
        if self.accept(","):
            step = self.parse_expr()
        self.expect("NEWLINE")
        body = self.parse_stmt_list()
        self._expect_enddo()
        return DoRange(var, start, stop, step, body, line)

    def _expect_enddo(self):
        if self.check("ENDDO"):
            self.advance()
        else:
            self.expect("END")
            self.expect("DO")
        self.expect("NEWLINE")

    def parse_call_stmt(self):
        line = self.cur().line
        self.expect("CALL")
        name = self.expect("ID").value
        args = []
        if self.accept("("):
            if not self.check(")"):
                args.append(self.parse_expr())
                while self.accept(","):
                    args.append(self.parse_expr())
            self.expect(")")
        self.expect("NEWLINE")
        return Call(name, args, line)

    # --- expressions (precedence climbing) ---
    def parse_expr(self):
        return self.parse_eqv()

    def parse_eqv(self):
        left = self.parse_or()
        while self.kind() in (".EQV.", ".NEQV."):
            op = self.advance().kind
            right = self.parse_or()
            left = BinOp(op, left, right)
        return left

    def parse_or(self):
        left = self.parse_and()
        while self.check(".OR."):
            self.advance()
            right = self.parse_and()
            left = BinOp(".OR.", left, right)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.check(".AND."):
            self.advance()
            right = self.parse_not()
            left = BinOp(".AND.", left, right)
        return left

    def parse_not(self):
        if self.check(".NOT."):
            self.advance()
            operand = self.parse_not()
            return UnaryOp(".NOT.", operand)
        return self.parse_rel()

    def parse_rel(self):
        left = self.parse_add()
        if self.kind() in REL_OPS:
            op = self.advance().kind
            right = self.parse_add()
            return BinOp(op, left, right)
        return left

    def parse_add(self):
        left = self.parse_mul()
        while self.kind() in ("+", "-"):
            op = self.advance().kind
            right = self.parse_mul()
            left = BinOp(op, left, right)
        return left

    def parse_mul(self):
        left = self.parse_unary()
        while self.kind() in ("*", "/"):
            op = self.advance().kind
            right = self.parse_unary()
            left = BinOp(op, left, right)
        return left

    def parse_unary(self):
        if self.kind() in ("+", "-"):
            op = self.advance().kind
            operand = self.parse_unary()
            return UnaryOp(op, operand)
        return self.parse_pow()

    def parse_pow(self):
        base = self.parse_atom()
        if self.check("**"):
            self.advance()
            exponent = self.parse_unary()
            return BinOp("**", base, exponent)
        return base

    def parse_atom(self):
        t = self.cur()
        if t.kind in ("REAL", "DOUBLE") and self.toks[self.pos + 1].kind == "(":
            # REAL(...)/DBLE-as-REAL used as the intrinsic conversion function,
            # not the type keyword -- REAL is a keyword token, not ID, so it
            # needs this special case to be callable like any other intrinsic.
            self.advance()
            name = "real"
            self.expect("(")
            args = []
            if not self.check(")"):
                args.append(self.parse_expr())
                while self.accept(","):
                    args.append(self.parse_expr())
            self.expect(")")
            return FuncCall(name, args)
        if t.kind == "INT":
            self.advance()
            return IntLit(t.value)
        if t.kind == "REAL":
            self.advance()
            return RealLit(t.value)
        if t.kind == "STR":
            self.advance()
            return StrLit(t.value)
        if t.kind == "BOOL":
            self.advance()
            return BoolLit(t.value)
        if t.kind == "(":
            self.advance()
            e = self.parse_expr()
            self.expect(")")
            return e
        if t.kind == "ID":
            self.advance()
            if self.accept("("):
                args = []
                if not self.check(")"):
                    args.append(self.parse_expr())
                    while self.accept(","):
                        args.append(self.parse_expr())
                self.expect(")")
                return FuncCall(t.value, args)
            return Name(t.value)
        raise ParseError(f"line {t.line}: unexpected token {t.kind!r} in expression")


def parse(tokens):
    return Parser(tokens).parse_module()
