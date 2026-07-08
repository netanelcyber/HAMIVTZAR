"""x86-64 code generator: annotated AST (semantic.py) -> GNU-as assembly
(Intel syntax) for either Linux (SysV ABI) or Windows (Microsoft x64 ABI),
per target.py.

Design notes
------------
* Fortran passes actual arguments *by reference*: every argument crossing a
  CALL/function-call boundary is an address, always carried in an
  integer/pointer register. That means user-procedure calls only ever need
  `target.int_arg_regs` -- there is no float/int argument-classifier to
  reimplement. Runtime helpers (rt_print_int, sin, fmod, ...) are a separate,
  simpler case: fixed arity, by-value arguments, special-cased directly.
* Every local scalar/array lives in a fixed rbp-relative stack slot; nothing
  is register-allocated. A tiny stack machine (push left, evaluate right,
  pop, combine) implements expression evaluation. This trades performance
  for a small, obviously-correct code generator.
* Before every `call` (user procedure, runtime helper, or libm function) the
  generator dynamically re-aligns rsp to 16 bytes using a scratch register
  (r11) rather than statically tracking parity through the push-based
  expression evaluator -- simpler to get right, and correct on both target
  ABIs (Windows additionally needs 32 bytes of caller-allocated shadow
  space, added inside the same helper).
* Fortran's dummy arguments are pointers; a parameter's stack slot holds the
  *pointer*, so reading/writing it is one indirection more than an ordinary
  local. Arrays are never passed as arguments in this subset, so array slots
  always hold data directly.
"""

from ast_nodes import (
    Name, ArrayRef, FuncCall, BinOp, UnaryOp,
    IntLit, RealLit, BoolLit, StrLit,
    Assign, Print, ReadStmt, If, DoRange, DoWhile, Call, Return, Stop, Exit, Cycle, NoOp,
)
from intrinsics import INTRINSICS

REL_SETCC_INT = {
    ".EQ.": "sete", "==": "sete",
    ".NE.": "setne", "/=": "setne",
    ".LT.": "setl", "<": "setl",
    ".LE.": "setle", "<=": "setle",
    ".GT.": "setg", ">": "setg",
    ".GE.": "setge", ">=": "setge",
}
REL_SETCC_REAL = {
    ".EQ.": "sete", "==": "sete",
    ".NE.": "setne", "/=": "setne",
    ".LT.": "setb", "<": "setb",
    ".LE.": "setbe", "<=": "setbe",
    ".GT.": "seta", ">": "seta",
    ".GE.": "setae", ">=": "setae",
}

LIBM_1ARG = {"sin", "cos", "tan", "exp", "log"}


class CodegenError(Exception):
    pass


class CodeGenerator:
    def __init__(self, units_info, procedures, target):
        self.units_info = units_info
        self.procedures = procedures
        self.target = target
        self.const_lines = []
        self.const_counter = 0
        self.label_counter = 0
        self.offsets = {}          # name(lower) -> byte offset from rbp (current unit)
        self.symtab = {}           # current unit's symtab
        self.cur_offset = 0        # bump allocator for hidden temporaries
        self.loop_stack = []       # (continue_label, end_label)
        self.epilogue_label = None
        self.unit = None

    # ---- top level ----
    def generate(self, module):
        lines = [".intel_syntax noprefix", ".text"]
        for unit in module.units:
            lines.extend(self._gen_unit(unit))
        text = "\n".join(lines) + "\n"
        if self.const_lines:
            text += "\n.data\n" + "\n".join(self.const_lines) + "\n"
        return text

    def new_label(self, tag):
        self.label_counter += 1
        return f".L{tag}{self.label_counter}"

    def add_float_const(self, value):
        label = f".Lflt{self.const_counter}"
        self.const_counter += 1
        self.const_lines.append(f"{label}: .double {float(value)!r}")
        return label

    def add_string_const(self, s):
        label = f".Lstr{self.const_counter}"
        self.const_counter += 1
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        self.const_lines.append(f'{label}: .ascii "{escaped}"')
        return label, len(s)

    # ---- frame allocation ----
    def _alloc_frame(self, unit, symtab):
        offsets = {}
        off = 0
        for name in sorted(symtab):
            sym = symtab[name]
            size = 8 * (sym.dims[0] if sym.is_array and sym.dims else 1)
            off += size
            offsets[name] = off
        return offsets, off

    def alloc_temp(self):
        self.cur_offset += 8
        return self.cur_offset

    def slot(self, offset):
        return f"[rbp-{offset}]"

    # ---- calls ----
    def emit_call(self, lines, label):
        # r10 holds the 16-byte alignment fixup only up to the point it is
        # stashed in memory: registers are caller-saved, so nothing survives
        # across `call` except what we put on the stack ourselves. The dummy
        # 16-byte reservation (fixup + padding) keeps rsp a multiple of 16
        # while carrying the fixup safely through the call.
        lines.append("    mov r10, rsp")
        lines.append("    and r10, 15")
        lines.append("    sub rsp, r10")
        lines.append("    sub rsp, 16")
        lines.append("    mov [rsp], r10")
        if self.target.shadow_space:
            lines.append(f"    sub rsp, {self.target.shadow_space}")
        lines.append(f"    call {label}")
        if self.target.shadow_space:
            lines.append(f"    add rsp, {self.target.shadow_space}")
        lines.append("    mov r10, [rsp]")
        lines.append("    add rsp, 16")
        lines.append("    add rsp, r10")

    # ---- unit codegen ----
    def _gen_unit(self, unit):
        info = self.units_info[unit.name.lower()]
        self.symtab = info.symtab
        self.offsets, base_size = self._alloc_frame(unit, self.symtab)
        self.cur_offset = base_size
        self.unit = unit

        asm_name = "main" if unit.kind == "program" else f"frt_{unit.name.lower()}"
        self.epilogue_label = self.new_label("epilogue")

        body_lines = []
        for stmt in unit.body:
            self._gen_stmt(stmt, body_lines)

        frame_size = ((self.cur_offset + 15) // 16) * 16
        if frame_size == 0:
            frame_size = 16

        out = [f".globl {asm_name}", f"{asm_name}:", "    push rbp", "    mov rbp, rsp",
               f"    sub rsp, {frame_size}"]

        if unit.kind in ("subroutine", "function"):
            regs = self.target.int_arg_regs
            for i, pname in enumerate(unit.params):
                off = self.offsets[pname.lower()]
                if i < len(regs):
                    out.append(f"    mov {self.slot(off)}, {regs[i]}")
                else:
                    stack_idx = i - len(regs)
                    out.append(f"    mov rax, [rbp+{16 + 8 * stack_idx}]")
                    out.append(f"    mov {self.slot(off)}, rax")

        out.extend(body_lines)
        out.append(f"{self.epilogue_label}:")
        if unit.kind == "function":
            ret_off = self.offsets[unit.name.lower()]
            if unit.result_type.base == "real":
                out.append(f"    movsd xmm0, {self.slot(ret_off)}")
            else:
                out.append(f"    mov rax, {self.slot(ret_off)}")
        elif unit.kind == "program":
            out.append("    xor eax, eax")
        out.append("    mov rsp, rbp")
        out.append("    pop rbp")
        out.append("    ret")
        return out

    # ---- statements ----
    def _gen_stmt(self, stmt, out):
        if isinstance(stmt, Assign):
            self._gen_assign(stmt, out)
        elif isinstance(stmt, Print):
            self._gen_print(stmt, out)
        elif isinstance(stmt, ReadStmt):
            self._gen_read(stmt, out)
        elif isinstance(stmt, If):
            self._gen_if(stmt, out)
        elif isinstance(stmt, DoRange):
            self._gen_do_range(stmt, out)
        elif isinstance(stmt, DoWhile):
            self._gen_do_while(stmt, out)
        elif isinstance(stmt, Call):
            self._gen_call_stmt(stmt, out)
        elif isinstance(stmt, Return):
            out.append(f"    jmp {self.epilogue_label}")
        elif isinstance(stmt, Stop):
            self.emit_call(out, "rt_exit")
        elif isinstance(stmt, Exit):
            out.append(f"    jmp {self.loop_stack[-1][1]}")
        elif isinstance(stmt, Cycle):
            out.append(f"    jmp {self.loop_stack[-1][0]}")
        elif isinstance(stmt, NoOp):
            pass
        else:
            raise CodegenError(f"unhandled statement {type(stmt).__name__}")

    def _lvalue_addr_to_rax(self, node, out):
        """Compute the address of a Name/ArrayRef lvalue into rax."""
        if isinstance(node, Name):
            sym = self.symtab[node.name.lower()]
            off = self.offsets[node.name.lower()]
            if sym.is_param:
                out.append(f"    mov rax, {self.slot(off)}")
            else:
                out.append(f"    lea rax, {self.slot(off)}")
        elif isinstance(node, ArrayRef):
            sym = self.symtab[node.name.lower()]
            off = self.offsets[node.name.lower()]
            self._gen_expr(node.index, out)
            out.append("    mov rcx, rax")
            out.append("    dec rcx")
            out.append(f"    lea rax, [rbp-{off}+rcx*8]")
        else:
            raise CodegenError("invalid lvalue")

    def _gen_assign(self, stmt, out):
        target = stmt.target
        if isinstance(target, ArrayRef):
            self._lvalue_addr_to_rax(target, out)
            tmp = self.alloc_temp()
            out.append(f"    mov {self.slot(tmp)}, rax")
            self._gen_expr_coerced(stmt.value, target.type, out)
            out.append(f"    mov rcx, {self.slot(tmp)}")
            if target.type == "real":
                out.append("    movsd [rcx], xmm0")
            else:
                out.append("    mov [rcx], rax")
        else:
            sym = self.symtab[target.name.lower()]
            off = self.offsets[target.name.lower()]
            self._gen_expr_coerced(stmt.value, target.type, out)
            if sym.is_param:
                out.append("    mov rdx, rax" if target.type != "real" else "    movsd xmm1, xmm0")
                out.append(f"    mov rax, {self.slot(off)}")
                if target.type == "real":
                    out.append("    movsd [rax], xmm1")
                else:
                    out.append("    mov [rax], rdx")
            else:
                if target.type == "real":
                    out.append(f"    movsd {self.slot(off)}, xmm0")
                else:
                    out.append(f"    mov {self.slot(off)}, rax")

    def _gen_expr_coerced(self, node, want_type, out):
        self._gen_expr(node, out)
        if want_type == "real" and node.type != "real":
            out.append("    cvtsi2sd xmm0, rax")
        elif want_type != "real" and node.type == "real":
            out.append("    cvttsd2si rax, xmm0")

    def _gen_print(self, stmt, out):
        for item in stmt.items:
            if isinstance(item, StrLit):
                label, length = self.add_string_const(item.value)
                regs = self.target.int_arg_regs
                out.append(f"    lea {regs[0]}, {label}[rip]")
                out.append(f"    mov {regs[1]}, {length}")
                self.emit_call(out, "rt_print_str")
            else:
                self._gen_expr(item, out)
                regs = self.target.int_arg_regs
                if item.type == "real":
                    self.emit_call(out, "rt_print_real")
                elif item.type == "logical":
                    out.append(f"    mov {regs[0]}, rax")
                    self.emit_call(out, "rt_print_logical")
                else:
                    out.append(f"    mov {regs[0]}, rax")
                    self.emit_call(out, "rt_print_int")
            self.emit_call(out, "rt_print_space")
        self.emit_call(out, "rt_print_newline")

    def _gen_read(self, stmt, out):
        for target in stmt.items:
            is_real = target.type == "real"
            self.emit_call(out, "rt_read_real" if is_real else "rt_read_int")
            if isinstance(target, ArrayRef):
                # stash the freshly-read value before clobbering rax while
                # computing the element address
                val_tmp = self.alloc_temp()
                if is_real:
                    out.append(f"    movsd {self.slot(val_tmp)}, xmm0")
                else:
                    out.append(f"    mov {self.slot(val_tmp)}, rax")
                self._lvalue_addr_to_rax(target, out)
                out.append("    mov rcx, rax")
                if is_real:
                    out.append(f"    movsd xmm0, {self.slot(val_tmp)}")
                    out.append("    movsd [rcx], xmm0")
                else:
                    out.append(f"    mov rax, {self.slot(val_tmp)}")
                    out.append("    mov [rcx], rax")
            else:
                sym = self.symtab[target.name.lower()]
                off = self.offsets[target.name.lower()]
                if sym.is_param:
                    if is_real:
                        out.append("    movsd xmm1, xmm0")
                    else:
                        out.append("    mov rdx, rax")
                    out.append(f"    mov rax, {self.slot(off)}")
                    if is_real:
                        out.append("    movsd [rax], xmm1")
                    else:
                        out.append("    mov [rax], rdx")
                else:
                    if is_real:
                        out.append(f"    movsd {self.slot(off)}, xmm0")
                    else:
                        out.append(f"    mov {self.slot(off)}, rax")

    def _gen_if(self, stmt, out):
        end_label = self.new_label("ifend")
        branches = stmt.branches
        for i, (cond, body) in enumerate(branches):
            is_last = i == len(branches) - 1
            if cond is not None:
                next_label = self.new_label("ifnext") if not is_last else end_label
                self._gen_expr(cond, out)
                out.append("    cmp rax, 0")
                out.append(f"    je {next_label}")
                for s in body:
                    self._gen_stmt(s, out)
                if not is_last:
                    out.append(f"    jmp {end_label}")
                    out.append(f"{next_label}:")
            else:
                for s in body:
                    self._gen_stmt(s, out)
        out.append(f"{end_label}:")

    def _gen_do_range(self, stmt, out):
        i_off = self.offsets[stmt.var.lower()]
        end_off = self.alloc_temp()
        step_off = self.alloc_temp()
        trip_off = self.alloc_temp()

        self._gen_expr(stmt.start, out)
        out.append(f"    mov {self.slot(i_off)}, rax")
        self._gen_expr(stmt.stop, out)
        out.append(f"    mov {self.slot(end_off)}, rax")
        if stmt.step is not None:
            self._gen_expr(stmt.step, out)
            out.append(f"    mov {self.slot(step_off)}, rax")
        else:
            out.append(f"    mov qword ptr {self.slot(step_off)}, 1")

        out.append(f"    mov rax, {self.slot(end_off)}")
        out.append(f"    sub rax, {self.slot(i_off)}")
        out.append(f"    add rax, {self.slot(step_off)}")
        out.append("    cqo")
        out.append(f"    mov rcx, {self.slot(step_off)}")
        out.append("    idiv rcx")
        out.append(f"    mov {self.slot(trip_off)}, rax")

        test_label = self.new_label("dotest")
        cont_label = self.new_label("docont")
        end_label = self.new_label("doend")
        out.append(f"{test_label}:")
        out.append(f"    mov rax, {self.slot(trip_off)}")
        out.append("    cmp rax, 0")
        out.append(f"    jle {end_label}")

        self.loop_stack.append((cont_label, end_label))
        for s in stmt.body:
            self._gen_stmt(s, out)
        self.loop_stack.pop()

        out.append(f"{cont_label}:")
        out.append(f"    mov rax, {self.slot(i_off)}")
        out.append(f"    mov rcx, {self.slot(step_off)}")
        out.append("    add rax, rcx")
        out.append(f"    mov {self.slot(i_off)}, rax")
        out.append(f"    mov rax, {self.slot(trip_off)}")
        out.append("    dec rax")
        out.append(f"    mov {self.slot(trip_off)}, rax")
        out.append(f"    jmp {test_label}")
        out.append(f"{end_label}:")

    def _gen_do_while(self, stmt, out):
        test_label = self.new_label("whtest")
        end_label = self.new_label("whend")
        out.append(f"{test_label}:")
        self._gen_expr(stmt.cond, out)
        out.append("    cmp rax, 0")
        out.append(f"    je {end_label}")
        self.loop_stack.append((test_label, end_label))
        for s in stmt.body:
            self._gen_stmt(s, out)
        self.loop_stack.pop()
        out.append(f"    jmp {test_label}")
        out.append(f"{end_label}:")

    # ---- user procedure calls (by-reference arguments) ----
    def _gen_arg_addresses(self, args, out):
        """Materialize each actual argument's address into a hidden temp slot,
        returning the list of temp offsets in order."""
        addr_offsets = []
        for arg in args:
            tmp = self.alloc_temp()
            if isinstance(arg, (Name, ArrayRef)):
                self._lvalue_addr_to_rax(arg, out)
            else:
                self._gen_expr(arg, out)
                val_tmp = self.alloc_temp()
                if arg.type == "real":
                    out.append(f"    movsd {self.slot(val_tmp)}, xmm0")
                else:
                    out.append(f"    mov {self.slot(val_tmp)}, rax")
                out.append(f"    lea rax, {self.slot(val_tmp)}")
            out.append(f"    mov {self.slot(tmp)}, rax")
            addr_offsets.append(tmp)
        return addr_offsets

    def _gen_call_stmt(self, stmt, out):
        proc = self.procedures[stmt.name.lower()]
        addr_offsets = self._gen_arg_addresses(stmt.args, out)
        regs = self.target.int_arg_regs
        for i, off in enumerate(addr_offsets):
            if i < len(regs):
                out.append(f"    mov {regs[i]}, {self.slot(off)}")
        self.emit_call(out, f"frt_{stmt.name.lower()}")

    def _gen_user_func_call(self, node, out):
        proc = self.procedures[node.name.lower()]
        addr_offsets = self._gen_arg_addresses(node.args, out)
        regs = self.target.int_arg_regs
        for i, off in enumerate(addr_offsets):
            if i < len(regs):
                out.append(f"    mov {regs[i]}, {self.slot(off)}")
        self.emit_call(out, f"frt_{node.name.lower()}")

    # ---- expressions ----
    def _gen_expr(self, node, out):
        if isinstance(node, IntLit):
            out.append(f"    mov rax, {node.value}")
        elif isinstance(node, BoolLit):
            out.append(f"    mov rax, {1 if node.value else 0}")
        elif isinstance(node, RealLit):
            label = self.add_float_const(node.value)
            out.append(f"    movsd xmm0, {label}[rip]")
        elif isinstance(node, Name):
            sym = self.symtab[node.name.lower()]
            off = self.offsets[node.name.lower()]
            if sym.is_param:
                out.append(f"    mov rax, {self.slot(off)}")
                if node.type == "real":
                    out.append("    movsd xmm0, [rax]")
                else:
                    out.append("    mov rax, [rax]")
            else:
                if node.type == "real":
                    out.append(f"    movsd xmm0, {self.slot(off)}")
                else:
                    out.append(f"    mov rax, {self.slot(off)}")
        elif isinstance(node, ArrayRef):
            off = self.offsets[node.name.lower()]
            self._gen_expr(node.index, out)
            out.append("    mov rcx, rax")
            out.append("    dec rcx")
            out.append(f"    lea rax, [rbp-{off}+rcx*8]")
            if node.type == "real":
                out.append("    movsd xmm0, [rax]")
            else:
                out.append("    mov rax, [rax]")
        elif isinstance(node, UnaryOp):
            self._gen_unary(node, out)
        elif isinstance(node, BinOp):
            self._gen_binop(node, out)
        elif isinstance(node, FuncCall):
            self._gen_funccall(node, out)
        else:
            raise CodegenError(f"unhandled expression {type(node).__name__}")

    def _gen_unary(self, node, out):
        self._gen_expr(node.operand, out)
        if node.op == "-":
            if node.type == "real":
                l1 = self.new_label("negdone")
                out.append("    xorpd xmm1, xmm1")
                out.append("    subsd xmm1, xmm0")
                out.append("    movsd xmm0, xmm1")
            else:
                out.append("    neg rax")
        elif node.op == "+":
            pass
        elif node.op == ".NOT.":
            out.append("    xor rax, 1")

    def _push_val(self, typ, out):
        if typ == "real":
            out.append("    sub rsp, 8")
            out.append("    movsd [rsp], xmm0")
        else:
            out.append("    push rax")

    def _pop_val(self, typ, dst, out):
        if typ == "real":
            out.append(f"    movsd {dst}, [rsp]")
            out.append("    add rsp, 8")
        else:
            out.append(f"    pop {dst}")

    def _gen_binop(self, node, out):
        op = node.op
        result_type = node.type
        if op in (".AND.", ".OR.", ".EQV.", ".NEQV."):
            self._gen_expr(node.left, out)
            out.append("    push rax")
            self._gen_expr(node.right, out)
            out.append("    pop rbx")
            if op == ".AND.":
                out.append("    and rax, rbx")
            elif op == ".OR.":
                out.append("    or rax, rbx")
            elif op == ".EQV.":
                out.append("    cmp rax, rbx")
                out.append("    sete al")
                out.append("    movzx eax, al")
            else:
                out.append("    cmp rax, rbx")
                out.append("    setne al")
                out.append("    movzx eax, al")
            return

        is_real = result_type == "real" or node.left.type == "real" or node.right.type == "real"
        if op in REL_SETCC_INT:
            self._gen_expr(node.left, out)
            if is_real and node.left.type != "real":
                out.append("    cvtsi2sd xmm0, rax")
            self._push_val("real" if is_real else "integer", out)
            self._gen_expr(node.right, out)
            if is_real and node.right.type != "real":
                out.append("    cvtsi2sd xmm0, rax")
            if is_real:
                out.append("    movsd xmm1, xmm0")
                self._pop_val("real", "xmm0", out)
                out.append("    comisd xmm0, xmm1")
                setcc = REL_SETCC_REAL[op]
            else:
                self._pop_val("integer", "rbx", out)
                out.append("    cmp rbx, rax")
                setcc = REL_SETCC_INT[op]
            out.append(f"    {setcc} al")
            out.append("    movzx eax, al")
            return

        # arithmetic: +, -, *, /, **
        self._gen_expr(node.left, out)
        if result_type == "real" and node.left.type != "real":
            out.append("    cvtsi2sd xmm0, rax")
        self._push_val(result_type, out)
        self._gen_expr(node.right, out)
        if result_type == "real" and node.right.type != "real":
            out.append("    cvtsi2sd xmm0, rax")

        if result_type == "real":
            out.append("    movsd xmm1, xmm0")     # xmm1 = right (temp)
            self._pop_val("real", "xmm0", out)      # xmm0 = left
            # now xmm0=left, xmm1=right
            if op == "+":
                out.append("    addsd xmm0, xmm1")
            elif op == "-":
                out.append("    subsd xmm0, xmm1")
            elif op == "*":
                out.append("    mulsd xmm0, xmm1")
            elif op == "/":
                out.append("    divsd xmm0, xmm1")
            elif op == "**":
                self.emit_call(out, "pow")
            else:
                raise CodegenError(f"unsupported real operator {op}")
        else:
            self._pop_val("integer", "rbx", out)    # rbx = left, rax = right
            if op == "+":
                out.append("    add rax, rbx")
            elif op == "-":
                out.append("    sub rbx, rax")
                out.append("    mov rax, rbx")
            elif op == "*":
                out.append("    imul rax, rbx")
            elif op == "/":
                out.append("    mov rcx, rax")
                out.append("    mov rax, rbx")
                out.append("    cqo")
                out.append("    idiv rcx")
            elif op == "**":
                regs = self.target.int_arg_regs
                out.append(f"    mov {regs[1]}, rax")
                out.append(f"    mov {regs[0]}, rbx")
                self.emit_call(out, "rt_ipow")
            else:
                raise CodegenError(f"unsupported integer operator {op}")

    def _gen_funccall(self, node, out):
        key = node.name.lower()
        if key in INTRINSICS:
            self._gen_intrinsic(node, out)
        else:
            self._gen_user_func_call(node, out)

    def _gen_intrinsic(self, node, out):
        key = node.name.lower()
        args = node.args
        if key == "sqrt":
            self._gen_expr(args[0], out)
            if args[0].type != "real":
                out.append("    cvtsi2sd xmm0, rax")
            out.append("    sqrtsd xmm0, xmm0")
            return
        if key in ("real", "dble"):
            self._gen_expr(args[0], out)
            if args[0].type != "real":
                out.append("    cvtsi2sd xmm0, rax")
            return
        if key == "int":
            self._gen_expr(args[0], out)
            if args[0].type == "real":
                out.append("    cvttsd2si rax, xmm0")
            return
        if key == "abs":
            self._gen_expr(args[0], out)
            if node.type == "real":
                done = self.new_label("absdone")
                out.append("    xorpd xmm1, xmm1")
                out.append("    comisd xmm0, xmm1")
                out.append(f"    jae {done}")
                out.append("    xorpd xmm2, xmm2")
                out.append("    subsd xmm2, xmm0")
                out.append("    movsd xmm0, xmm2")
                out.append(f"{done}:")
            else:
                out.append("    mov rdx, rax")
                out.append("    sar rdx, 63")
                out.append("    xor rax, rdx")
                out.append("    sub rax, rdx")
            return
        if key == "mod":
            is_real = node.type == "real"
            self._gen_expr(args[0], out)
            if is_real and args[0].type != "real":
                out.append("    cvtsi2sd xmm0, rax")
            self._push_val("real" if is_real else "integer", out)
            self._gen_expr(args[1], out)
            if is_real and args[1].type != "real":
                out.append("    cvtsi2sd xmm0, rax")
            if is_real:
                out.append("    movsd xmm1, xmm0")
                self._pop_val("real", "xmm0", out)
                self.emit_call(out, "fmod")
            else:
                out.append("    mov rcx, rax")
                self._pop_val("integer", "rax", out)
                out.append("    cqo")
                out.append("    idiv rcx")
                out.append("    mov rax, rdx")
            return
        if key in ("max", "min"):
            is_real = node.type == "real"
            self._gen_expr(args[0], out)
            if is_real and args[0].type != "real":
                out.append("    cvtsi2sd xmm0, rax")
            for a in args[1:]:
                self._push_val("real" if is_real else "integer", out)
                self._gen_expr(a, out)
                if is_real and a.type != "real":
                    out.append("    cvtsi2sd xmm0, rax")
                if is_real:
                    out.append("    movsd xmm1, xmm0")
                    self._pop_val("real", "xmm0", out)
                    if key == "max":
                        out.append("    maxsd xmm0, xmm1")
                    else:
                        out.append("    minsd xmm0, xmm1")
                else:
                    self._pop_val("integer", "rbx", out)
                    out.append("    cmp rbx, rax")
                    if key == "max":
                        out.append("    cmovg rax, rbx")
                    else:
                        out.append("    cmovl rax, rbx")
            return
        if key in LIBM_1ARG:
            self._gen_expr(args[0], out)
            if args[0].type != "real":
                out.append("    cvtsi2sd xmm0, rax")
            self.emit_call(out, key)
            return
        raise CodegenError(f"unhandled intrinsic {key}")


def generate(module, units_info, procedures, target):
    return CodeGenerator(units_info, procedures, target).generate(module)
