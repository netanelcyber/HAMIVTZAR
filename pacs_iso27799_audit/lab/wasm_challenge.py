"""Builds a tiny WebAssembly module used as a local reverse-engineering
exercise -- see lab/README.md's "WASM reverse-engineering exercise"
section for how to approach it.

If you're doing that exercise: stop here and fetch the compiled module
from the running mock server instead (GET /static/access-check.wasm,
or use fetch_wasm_challenge.py) and disassemble it with inspect_wasm.py.
Reading this file's bytecode-construction code is equivalent to reading a
solved disassembly.

The module exports one function, `check_code(i32) -> i32`. It implements a
simple client-side "looks valid" checksum over a 3-digit access code --
this is NOT the real secret comparison, which still only happens
server-side in mock_patient_portal.py's /instant-access. It mirrors a real
(and flawed) pattern: some client apps run a cheap client-side pre-check
before bothering the server. That check's logic ships to the browser as
plain bytecode and can always be extracted and disassembled -- WASM is
not obfuscation, and a client-side check is never a substitute for the
server-side control it sits in front of (see control AC-8's remediation
note in ../controls.py).
"""

from __future__ import annotations


def _uleb128(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _section(section_id: int, content: bytes) -> bytes:
    return bytes([section_id]) + _uleb128(len(content)) + content


def build_access_check_module() -> bytes:
    magic = b"\x00asm"
    version = b"\x01\x00\x00\x00"

    # Type section: one function type, (i32) -> i32.
    type_section = _section(1, bytes([0x01, 0x60, 0x01, 0x7F, 0x01, 0x7F]))

    # Function section: function 0 uses type 0.
    function_section = _section(3, bytes([0x01, 0x00]))

    # Export section: export function 0 as "check_code".
    name = b"check_code"
    export_entry = _uleb128(len(name)) + name + bytes([0x00, 0x00])
    export_section = _section(7, _uleb128(1) + export_entry)

    # Code section: function 0's body.
    body_expr = bytes([
        0x20, 0x00,        # local.get 0
        0x41, 0x1F,        # i32.const 31
        0x6C,              # i32.mul
        0x41, 0x07,        # i32.const 7
        0x6A,              # i32.add
        0x41, 0xE8, 0x07,  # i32.const 1000
        0x70,              # i32.rem_u
        0x41, 0x2A,        # i32.const 42
        0x46,              # i32.eq
        0x0B,              # end
    ])
    body = bytes([0x00]) + body_expr  # 0 additional local declarations
    code_section = _section(10, _uleb128(1) + _uleb128(len(body)) + body)

    return magic + version + type_section + function_section + export_section + code_section


if __name__ == "__main__":
    import sys
    sys.stdout.buffer.write(build_access_check_module())
