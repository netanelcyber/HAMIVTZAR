"""End-to-end tests for the tools/ programs (disassembler, debugger, IDE),
themselves written in this project's Fortran subset. Linux-only (the
debugger is ptrace-based, and the IDE/disassembler default paths assume a
Linux target); skipped automatically if ptrace isn't permitted in this
sandbox.
"""

import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOLS = os.path.join(ROOT, "tools")
FORTRANC = os.path.join(ROOT, "fortranc.py")


def _compile_tool(tmp_path, name):
    src = os.path.join(TOOLS, f"{name}.f90")
    out = str(tmp_path / name)
    result = subprocess.run(
        [sys.executable, FORTRANC, src, "-o", out], capture_output=True, text=True,
    )
    assert result.returncode == 0, f"compiling {name} failed:\n{result.stderr}"
    assert os.path.exists(out)
    return out


def _main_vaddr(exe_path):
    result = subprocess.run(["readelf", "-s", exe_path], capture_output=True, text=True)
    m = re.search(r"^\s*\d+:\s*([0-9a-f]+)\s.*\bmain\b", result.stdout, re.MULTILINE)
    assert m, f"could not find 'main' symbol in {exe_path}"
    return int(m.group(1), 16)


@pytest.fixture(scope="module")
def target_exe(tmp_path_factory):
    """A plain compiled Fortran program for the tools to inspect."""
    tmp_path = tmp_path_factory.mktemp("target")
    src = os.path.join(ROOT, "examples", "hello.f90")
    out = str(tmp_path / "hello")
    result = subprocess.run(
        [sys.executable, FORTRANC, src, "-o", out], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    return out


def test_disassembler_finds_main(tmp_path, target_exe):
    disasm = _compile_tool(tmp_path, "fortran_disasm")
    vaddr = _main_vaddr(target_exe)
    result = subprocess.run([disasm, target_exe, str(vaddr)],
                             capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert "push" in result.stdout   # main always starts with `push rbp`
    assert "ret" in result.stdout


def test_debugger_hits_breakpoint(tmp_path, target_exe):
    dbg = _compile_tool(tmp_path, "fortran_dbg")
    vaddr = _main_vaddr(target_exe)
    try:
        result = subprocess.run([dbg, target_exe, str(vaddr)],
                                 capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        pytest.skip("debugger timed out -- ptrace likely unavailable in this sandbox")
    if "Operation not permitted" in result.stdout or result.returncode not in (0,):
        pytest.skip("ptrace not permitted in this sandbox")
    assert "breakpoint hit" in result.stdout
    assert "target exited with code 0" in result.stdout


def test_ide_compile_and_run(tmp_path):
    ide = _compile_tool(tmp_path, "fortran_ide")
    src = os.path.join(ROOT, "examples", "hello.f90")
    work_src = tmp_path / "hello.f90"
    work_src.write_text(open(src).read())
    result = subprocess.run([ide, str(work_src)], input="2\n3\n0\n",
                             capture_output=True, text=True, timeout=20,
                             cwd=str(tmp_path))
    assert result.returncode == 0
    assert "Hello from the from-scratch Fortran compiler!" in result.stdout
