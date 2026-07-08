"""End-to-end tests: compile each example program for both targets, run it
(natively for Linux, under Wine for Windows if available), and check stdout.
"""

import os
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXAMPLES = os.path.join(ROOT, "examples")
FORTRANC = os.path.join(ROOT, "fortranc.py")

WINE = shutil.which("wine64") or (
    "/usr/lib/wine/wine64" if os.path.exists("/usr/lib/wine/wine64") else None
)

EXPECTED = {
    "hello.f90": "Hello from the from-scratch Fortran compiler! \n",
    "factorial.f90": "factorial of 10 is 3628800 \n",
    "fibonacci.f90": "".join(f"{n} \n" for n in
                             [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]),
    "ifelse.f90": "".join(s + " \n" for s in
                          ["1", "2", "fizz", "4", "buzz", "fizz", "7", "8", "fizz",
                           "buzz", "11", "fizz", "13", "14", "fizzbuzz"]),
    "arrays.f90": "sum of squares 1..10 = 385 \naverage = 38.5 \n",
    "subprograms.f90": "after swap a= 7 b= 3 \nfactorial(5) = 120 \n",
    "bubble_sort.f90": "".join(f"{n} \n" for n in [1, 2, 3, 5, 8, 9]),
    "matmul.f90": "".join(s + " \n" for s in
                          ["1 1 110", "1 2 146", "2 1 200", "2 2 266"]),
    "primes.f90": "".join(f"{p} \n" for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]) +
                  "total primes up to 30 = 10 \n",
}


def _compile(tmp_path, name, target):
    src = os.path.join(EXAMPLES, name)
    out = str(tmp_path / f"{name}.{target}.out")
    result = subprocess.run(
        [sys.executable, FORTRANC, src, "-o", out, "--target", target],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"compile failed for {name} ({target}):\n{result.stderr}"
    suffix = ".exe" if target == "windows" else ""
    exe = out + suffix
    assert os.path.exists(exe)
    return exe


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_linux_target(tmp_path, name):
    exe = _compile(tmp_path, name, "linux")
    result = subprocess.run([exe], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert result.stdout == EXPECTED[name]


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_windows_target(tmp_path, name):
    if WINE is None:
        pytest.skip("wine64 not available to execute Windows binaries")
    exe = _compile(tmp_path, name, "windows")
    env = dict(os.environ, WINEDEBUG="-all")
    result = subprocess.run([WINE, exe], capture_output=True, text=True,
                             timeout=30, env=env)
    assert result.returncode == 0
    assert result.stdout == EXPECTED[name]
