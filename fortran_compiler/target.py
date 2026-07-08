"""Target machine descriptions: x86-64 Linux (SysV ABI) and x86-64 Windows (MS x64 ABI).

Fortran passes actual arguments *by reference*, so every subprogram argument
crossing a CALL boundary is a 64-bit address. That means our calling-convention
handling only ever needs an integer/pointer argument register list per target;
the tiny fixed-signature runtime helpers (rt_print_int, rt_print_real, ...)
are special-cased directly in codegen instead of going through a generic
argument-classifier.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Target:
    name: str
    int_arg_regs: tuple      # registers used for integer/pointer args, in order
    shadow_space: int        # bytes of caller-allocated shadow space before a call
    exe_suffix: str          # filename suffix for produced executables
    cc: tuple                # command used to assemble+link (compiler driver)
    extra_cflags: tuple = ()  # extra flags appended to every assemble/link invocation


LINUX_X64 = Target(
    name="linux-x64",
    int_arg_regs=("rdi", "rsi", "rdx", "rcx", "r8", "r9"),
    shadow_space=0,
    exe_suffix="",
    cc=("gcc",),
    # Non-PIE: fixed load address, so a static address from the disassembler
    # or `nm`/`readelf` is directly usable by the ptrace-based debugger with
    # no ASLR-base bookkeeping (matches how gdb defaults to disabling ASLR
    # for the same reason, just done at link time instead of at attach time).
    extra_cflags=("-no-pie",),
)

WINDOWS_X64 = Target(
    name="windows-x64",
    int_arg_regs=("rcx", "rdx", "r8", "r9"),
    shadow_space=32,
    exe_suffix=".exe",
    cc=("x86_64-w64-mingw32-gcc",),
)

TARGETS = {
    "linux": LINUX_X64,
    "linux-x64": LINUX_X64,
    "windows": WINDOWS_X64,
    "windows-x64": WINDOWS_X64,
    "win64": WINDOWS_X64,
}


def resolve_target(name: str) -> Target:
    try:
        return TARGETS[name.lower()]
    except KeyError:
        raise ValueError(
            f"unknown target '{name}', expected one of: {sorted(set(TARGETS))}"
        )
