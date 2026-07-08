#!/usr/bin/env python3
"""CLI driver: Fortran source -> x86-64 assembly -> native executable.

    fortranc.py input.f90 -o output [--target linux|windows] [-S] [--keep-asm]

Pipeline: lexer -> parser -> semantic -> codegen -> assemble/link via the
target's compiler driver (gcc for Linux, x86_64-w64-mingw32-gcc for Windows),
linking in runtime.c (the small libc-based I/O shim; see its docstring).
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import tokenize, LexError
from parser import parse, ParseError
from semantic import analyze, SemanticError
from codegen import generate, CodegenError
from target import resolve_target

HERE = os.path.dirname(os.path.abspath(__file__))
RUNTIME_C = os.path.join(HERE, "runtime.c")


class CompileError(Exception):
    pass


def compile_source(source: str, target):
    try:
        tokens = tokenize(source)
        module = parse(tokens)
        units_info, procedures = analyze(module)
        asm = generate(module, units_info, procedures, target)
    except (LexError, ParseError, SemanticError, CodegenError) as e:
        raise CompileError(str(e)) from e
    return asm


def build(input_path, output_path, target, keep_asm=False, emit_asm_only=False):
    with open(input_path, "r") as f:
        source = f.read()
    asm = compile_source(source, target)

    asm_path = output_path + ".s" if not emit_asm_only else output_path
    with open(asm_path, "w") as f:
        f.write(asm)

    if emit_asm_only:
        return asm_path

    exe_path = output_path + target.exe_suffix
    cmd = list(target.cc) + ["-std=c2x", asm_path, RUNTIME_C, "-o", exe_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not keep_asm:
        os.remove(asm_path)
    if result.returncode != 0:
        raise CompileError(f"assemble/link failed:\n{result.stderr}")
    return exe_path


def main():
    ap = argparse.ArgumentParser(description="Fortran-subset compiler targeting x86-64")
    ap.add_argument("input", help="Fortran source file")
    ap.add_argument("-o", "--output", default="a.out", help="output executable path (suffix added for Windows)")
    ap.add_argument("--target", default="linux", help="linux (default) or windows")
    ap.add_argument("-S", action="store_true", help="emit assembly only, don't assemble/link")
    ap.add_argument("--keep-asm", action="store_true", help="keep the generated .s file")
    args = ap.parse_args()

    target = resolve_target(args.target)
    try:
        out = build(args.input, args.output, target, keep_asm=args.keep_asm, emit_asm_only=args.S)
    except CompileError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    print(out)


if __name__ == "__main__":
    main()
