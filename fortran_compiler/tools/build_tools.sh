#!/usr/bin/env bash
# Builds the disassembler/debugger/IDE (themselves written in this
# project's Fortran subset) into tools/bin/. fortran_ide.f90 shells out to
# fortran_disasm and fortran_dbg via hardcoded paths, so this exact
# directory layout matters.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p tools/bin
for t in fortran_disasm fortran_dbg fortran_ide; do
    echo "building $t..."
    python3 fortranc.py "tools/$t.f90" -o "tools/bin/$t"
done
echo "done: tools/bin/{fortran_disasm,fortran_dbg,fortran_ide}"
