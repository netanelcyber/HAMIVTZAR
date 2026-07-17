"""Minimal, dependency-free WebAssembly binary disassembler.

Parses a .wasm module's structure (type/function/export/code sections) and
prints a human-readable, wat-like opcode listing for each function body.
Covers a useful subset of numeric/local/control opcodes -- enough to read
small modules like lab/wasm_challenge.py's, not a complete implementation
of the WASM spec (no memory/table/SIMD/multi-value support).

Usage:
    python -m pacs_iso27799_audit.lab.inspect_wasm path/to/module.wasm
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Tuple


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def eof(self) -> bool:
        return self.pos >= len(self.data)

    def byte(self) -> int:
        b = self.data[self.pos]
        self.pos += 1
        return b

    def bytes(self, n: int) -> bytes:
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def uleb128(self) -> int:
        result, shift = 0, 0
        while True:
            b = self.byte()
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                return result
            shift += 7

    def sleb128(self) -> int:
        result, shift = 0, 0
        while True:
            b = self.byte()
            result |= (b & 0x7F) << shift
            shift += 7
            if not (b & 0x80):
                if b & 0x40:
                    result |= -(1 << shift)
                return result

    def name(self) -> str:
        return self.bytes(self.uleb128()).decode("utf-8", errors="replace")


VALTYPE_NAMES = {0x7F: "i32", 0x7E: "i64", 0x7D: "f32", 0x7C: "f64"}

# opcode -> (mnemonic, operand reader name or None)
_NO_OPERAND = {
    0x00: "unreachable", 0x01: "nop", 0x0B: "end", 0x05: "else", 0x0F: "return",
    0x1A: "drop", 0x1B: "select",
    0x45: "i32.eqz", 0x46: "i32.eq", 0x47: "i32.ne",
    0x48: "i32.lt_s", 0x49: "i32.lt_u", 0x4A: "i32.gt_s", 0x4B: "i32.gt_u",
    0x4C: "i32.le_s", 0x4D: "i32.le_u", 0x4E: "i32.ge_s", 0x4F: "i32.ge_u",
    0x6A: "i32.add", 0x6B: "i32.sub", 0x6C: "i32.mul",
    0x6D: "i32.div_s", 0x6E: "i32.div_u", 0x6F: "i32.rem_s", 0x70: "i32.rem_u",
    0x71: "i32.and", 0x72: "i32.or", 0x73: "i32.xor",
    0x74: "i32.shl", 0x75: "i32.shr_s", 0x76: "i32.shr_u",
    0x77: "i32.rotl", 0x78: "i32.rotr",
}
_ULEB_OPERAND = {
    0x02: "block", 0x03: "loop", 0x04: "if",
    0x0C: "br", 0x0D: "br_if", 0x10: "call",
    0x20: "local.get", 0x21: "local.set", 0x22: "local.tee",
    0x23: "global.get", 0x24: "global.set",
}
_SLEB_OPERAND = {0x41: "i32.const"}


def disassemble_body(data: bytes) -> List[str]:
    r = _Reader(data)
    lines = []
    while not r.eof():
        op = r.byte()
        if op in _NO_OPERAND:
            lines.append(_NO_OPERAND[op])
        elif op in _ULEB_OPERAND:
            lines.append(f"{_ULEB_OPERAND[op]} {r.uleb128()}")
        elif op in _SLEB_OPERAND:
            lines.append(f"{_SLEB_OPERAND[op]} {r.sleb128()}")
        else:
            lines.append(f"<unknown opcode 0x{op:02X} at byte {r.pos - 1}>")
            break
    return lines


class Module:
    def __init__(self):
        self.types: List[Tuple[List[int], List[int]]] = []
        self.func_type_indices: List[int] = []
        self.exports: List[Tuple[str, int, int]] = []  # name, kind, index
        self.code: List[List[str]] = []  # disassembled opcode lines per function


def parse_module(data: bytes) -> Module:
    if data[:4] != b"\x00asm":
        raise ValueError("not a WASM module (bad magic number)")
    if data[4:8] != b"\x01\x00\x00\x00":
        raise ValueError(f"unsupported WASM version: {data[4:8]!r}")

    mod = Module()
    r = _Reader(data)
    r.pos = 8

    while not r.eof():
        section_id = r.byte()
        size = r.uleb128()
        section_end = r.pos + size

        if section_id == 1:  # type
            count = r.uleb128()
            for _ in range(count):
                form = r.byte()  # 0x60
                assert form == 0x60
                params = [r.byte() for _ in range(r.uleb128())]
                results = [r.byte() for _ in range(r.uleb128())]
                mod.types.append((params, results))
        elif section_id == 3:  # function
            count = r.uleb128()
            for _ in range(count):
                mod.func_type_indices.append(r.uleb128())
        elif section_id == 7:  # export
            count = r.uleb128()
            for _ in range(count):
                nm = r.name()
                kind = r.byte()
                idx = r.uleb128()
                mod.exports.append((nm, kind, idx))
        elif section_id == 10:  # code
            count = r.uleb128()
            for _ in range(count):
                body_size = r.uleb128()
                body_end = r.pos + body_size
                local_decl_count = r.uleb128()
                for _ in range(local_decl_count):
                    r.uleb128()  # count
                    r.byte()     # type
                expr = r.bytes(body_end - r.pos)
                mod.code.append(disassemble_body(expr))
                r.pos = body_end

        r.pos = section_end  # skip anything this parser doesn't decode

    return mod


def format_module(mod: Module) -> str:
    lines = []
    for i, (params, results) in enumerate(mod.types):
        p = ", ".join(VALTYPE_NAMES.get(t, hex(t)) for t in params)
        rr = ", ".join(VALTYPE_NAMES.get(t, hex(t)) for t in results)
        lines.append(f"type {i}: ({p}) -> ({rr})")
    for i, type_idx in enumerate(mod.func_type_indices):
        lines.append(f"func {i}: uses type {type_idx}")
    for name, kind, idx in mod.exports:
        kind_name = {0: "func", 1: "table", 2: "memory", 3: "global"}.get(kind, str(kind))
        lines.append(f'export "{name}" -> {kind_name} {idx}')
    for i, opcodes in enumerate(mod.code):
        lines.append(f"func {i} body:")
        for op in opcodes:
            lines.append(f"  {op}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("wasm_file")
    args = parser.parse_args(argv)

    with open(args.wasm_file, "rb") as f:
        data = f.read()

    mod = parse_module(data)
    print(format_module(mod))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
