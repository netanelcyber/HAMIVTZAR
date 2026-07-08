# fortran_compiler

A Fortran compiler built from scratch: hand-written lexer, recursive-descent
parser, semantic analyzer, and an x86-64 code generator that emits GNU-as
assembly directly (no LLVM, no reuse of gfortran/flang). It targets both
**Linux x86-64** (System V ABI, ELF) and **Windows x86-64** (Microsoft x64
ABI, PE, via the `mingw-w64` cross toolchain).

```
Fortran source
     |  lexer.py      (tokenize, handle continuation/comments)
     v
   tokens
     |  parser.py     (recursive descent -> AST)
     v
    AST                (ast_nodes.py)
     |  semantic.py   (symbol tables, type checking, array-vs-call resolution)
     v
 annotated AST
     |  codegen.py    (stack-frame locals, stack-machine expr eval, calls)
     v
 x86-64 assembly (Intel syntax, GNU as)
     |  gcc / x86_64-w64-mingw32-gcc  (assemble + link with runtime.c)
     v
  native executable
```

## Usage

```
python3 fortranc.py program.f90 -o program                 # Linux executable
python3 fortranc.py program.f90 -o program --target windows  # program.exe via mingw-w64
python3 fortranc.py program.f90 -o program -S               # emit program.s only, don't assemble
```

Requires `gcc`/`as`/`ld` for the Linux target, and
`gcc-mingw-w64-x86-64`/`binutils-mingw-w64-x86-64` for the Windows target
(`apt-get install gcc-mingw-w64-x86-64 binutils-mingw-w64-x86-64`).

## Supported language subset

- `PROGRAM` / `SUBROUTINE` / `FUNCTION` program units (external, one per file
  section; no `MODULE`, no internal/nested procedures)
- Types: `INTEGER`, `REAL`/`DOUBLE PRECISION` (both 64-bit), `LOGICAL`;
  N-dimensional arrays, column-major (Fortran order), e.g.
  `INTEGER :: a(3,4)`
- **Array arguments**: a whole array can be passed to a `SUBROUTINE`/
  `FUNCTION` by reference (`CALL sort(a, n)`), and a dummy array's extent
  may itself be another dummy argument (`INTEGER :: a(n)`) — the standard
  explicit-shape-array idiom, so array-processing subprograms (sorting,
  matrix ops, ...) work the way real Fortran code is written
- `TYPE, PARAMETER :: name = expr` compile-time constants, constant-folded
  wherever referenced (including as array bounds); plain
  `TYPE :: name = expr` initializes the variable once at unit entry;
  `TYPE, DIMENSION(...) ::` as an alternative to `name(...)`; `INTENT(...)`
  is accepted and ignored
- Expressions: `+ - * / **`, unary `+/-`, relational (`.EQ./==` etc.),
  logical (`.AND. .OR. .NOT. .EQV. .NEQV.`), with INTEGER/REAL promotion
- Statements: assignment, `PRINT *`/`WRITE(*,*)`, `READ *`/`READ(*,*)`,
  block `IF/THEN/ELSE IF/ELSE/END IF` (and single-line `IF (...) stmt`),
  `DO var = a,b[,c]` / `DO WHILE (...)`, `EXIT`, `CYCLE`, `CALL`, `RETURN`,
  `STOP`
- Intrinsics: `SQRT ABS MOD INT REAL DBLE MAX MIN SIN COS TAN ASIN ACOS ATAN
  ATAN2 SINH COSH TANH EXP LOG LOG10 FLOOR CEILING NINT SIGN`
- Arguments are passed by reference, matching Fortran semantics, so
  subroutines can mutate their arguments (`CALL swap(a, b)` works); more
  arguments than fit in registers (4 on Windows, 6 on Linux) spill correctly
  to the stack
- `RECURSIVE FUNCTION`/`SUBROUTINE` (accepted; recursion needs no special
  support since every call already gets its own stack frame — see
  `recursive_factorial.f90`)
- **Procedure arguments**: a `SUBROUTINE`/`FUNCTION` name can be passed as
  an actual argument (`CALL rk4(deriv, ...)`) and called indirectly through
  a dummy `EXTERNAL` argument (`REAL, EXTERNAL :: f` for a dummy function,
  bare `EXTERNAL sub` for a dummy subroutine) — enough to write a generic
  numerical solver once and hand it different equations (`rk4_ode.f90`)
- `IAND IOR IEOR NOT ISHFT` bitwise intrinsics
- **`CHARACTER(LEN=n)`** fixed-length, space-padded buffers: declaration,
  assignment from a string literal/another CHARACTER variable/`//`
  concatenation of those, `LEN()` (a compile-time constant here), passing
  a whole buffer to a subprogram by reference. Deliberately *not* general
  CHARACTER expressions — no `TRIM`/`LEN_TRIM`/substring/comparison; see
  "Toolchain" below for why this scope was enough to be useful anyway.
- **`BIND(C)`**: `TYPE, BIND(C) :: name` (or bare `EXTERNAL`+later use)
  declares `name` as a runtime.c symbol callable directly, by reference,
  with no static arity check — the mechanism `GET_COMMAND_ARGUMENT`,
  `COMMAND_ARGUMENT_COUNT`, and `EXECUTE_COMMAND_LINE` (real F2003/2008
  names) are built from, and how the tools below reach `fork`/`ptrace`/
  `waitpid` and byte-level file I/O
- Command-line args and shelling out: `GET_COMMAND_ARGUMENT`,
  `COMMAND_ARGUMENT_COUNT`, `EXECUTE_COMMAND_LINE`

Not supported: `MODULE`s, derived types, general `CHARACTER` expressions
(see above), allocatable/pointer attributes, formatted `PRINT`/`FORMAT`
strings, `GOTO` and statement labels, internal procedures, the standalone
F77-style `PARAMETER (name = value)` statement (use `TYPE, PARAMETER ::`
instead), explicit interfaces (so no static arity check on indirect/
`EXTERNAL`/`BIND(C)` calls — matches real Fortran without one).

> **Gotcha inherited from real Fortran:** declaring an ordinary variable
> with the same name as a procedure you intend to pass as an argument
> shadows the procedure reference in that scope. Don't (re)declare a
> function's name as a variable in the caller — it isn't needed there.

## How it works

- **No register allocator.** Every local scalar/array element lives in a
  fixed `rbp`-relative stack slot. Expressions are evaluated with a small
  stack machine (evaluate left, push, evaluate right, pop, combine). This
  trades performance for a code generator that's easy to get right.
- **Calling convention.** Fortran passes actual arguments by reference, so
  every argument crossing a `CALL`/function-call boundary is an address,
  always carried in an integer register — there's no float/int argument
  classifier to implement, unlike a C compiler's ABI layer. `target.py`
  supplies each target's integer argument-register list
  (`rdi,rsi,rdx,rcx,r8,r9` for SysV, `rcx,rdx,r8,r9` for Windows) and its
  shadow-space requirement (0 vs. 32 bytes).
- **Dynamic stack alignment.** Rather than statically track stack parity
  through the push-based expression evaluator, every `call` site
  re-aligns `rsp` to 16 bytes at runtime and restores it afterward
  (`codegen.py: emit_call`). The alignment fixup is stashed in *memory*,
  not a register — `r10`/`r11` are caller-saved, so anything living in a
  register does not survive across the `call` if the callee happens to
  clobber it (this was a real bug caught by the test suite: loops appeared
  to run once and silently stop because a runtime helper's own prologue
  clobbered the register holding the saved alignment amount).
- **I/O runtime (`runtime.c`).** A tiny, portable C shim (`rt_print_int`,
  `rt_print_real`, `rt_read_int`, ...) with fixed, simple signatures is
  linked into every compiled program. This keeps the code generator from
  having to reimplement libc's variadic-call ABI (`printf`) itself; it is
  compiled unchanged by native `gcc` (Linux) or `x86_64-w64-mingw32-gcc`
  (Windows). Written against C23 (`-std=c2x`, GCC 13's spelling for it) —
  `bool`/`true`/`false`/`nullptr`/`constexpr` as language keywords rather
  than `<stdbool.h>` macros, and `[[nodiscard]]`/`[[noreturn]]` attributes —
  the direction the next revision (informally C2y/"C29") continues.
- **Array addressing.** Arrays are column-major, computed at runtime as
  `base + Σ (index_k - 1) * stride_k` with `stride_1 = 1` — a plain loop
  over dimensions in `codegen.py: _gen_array_element_addr`, shared by reads,
  writes, and address-of (for passing to a subprogram). Local arrays need a
  compile-time-constant size (their storage is a fixed frame slot); array
  *parameters* don't have local storage at all (just the incoming pointer),
  so their extents may be ordinary runtime expressions — typically another
  dummy argument, as in `INTEGER :: a(n)`.
- **PARAMETER constants** are resolved by a small constant-folding
  evaluator (`semantic.py: _const_eval`) before anything else in a unit is
  analyzed, and substituted directly as literal nodes wherever referenced —
  they never get a stack slot, which is what lets them size a local array.
- **Procedure arguments.** A dummy `EXTERNAL` argument's stack slot holds
  the callee's *code address* directly (unlike an ordinary by-reference
  argument slot, which holds the address of a value one level further
  away), so calling through it is `mov reg, [slot]; call reg` — one
  indirection, not two. Passing a procedure as an actual argument is the
  mirror image: `lea rax, frt_name[rip]` for a known top-level
  `SUBROUTINE`/`FUNCTION`, or a plain forwarding load if the argument being
  passed is itself an `EXTERNAL` dummy of the *current* unit.
- **Stack-spilled arguments.** Arguments beyond the register count (4 on
  Windows, 6 on Linux) must land exactly where the callee's prologue reads
  them: `rbp+16`, `rbp+24`, ... on Linux, but `rbp+16+32`, `rbp+16+40`, ...
  on Windows, offset by the 32-byte shadow space the caller reserves right
  after the return address and saved `rbp`. The caller
  (`codegen.py: _emit_user_call`) writes them into one combined,
  16-byte-aligned stack reservation alongside the alignment fixup, rather
  than reusing the register-only path the small fixed-arity runtime/libm
  calls take.
- **`CHARACTER` storage.** A `CHARACTER(LEN=n)` variable is `n` *packed
  bytes* (not the 8-byte-per-element layout ordinary arrays use), so a
  buffer's address is directly usable as a C string pointer — passing one
  to a subprogram reuses the exact same "whole array by reference"
  mechanism (`WholeArrayRef`) that already existed for numeric arrays.
  Assignment (including `//` concatenation of several parts) is fully
  unrolled at compile time: every part's length is a compile-time
  constant, so there's no runtime length/loop-counter bookkeeping, just a
  fixed sequence of byte moves, truncated or space-padded to the target's
  declared length (`codegen.py: _gen_char_assign`).
- **`BIND(C)` calls** reuse the identical by-reference argument-passing
  path as ordinary Fortran-to-Fortran calls (`_emit_user_call`) — the only
  difference is the call target is the bare C symbol name instead of an
  `frt_`-prefixed label, and there's no arity check. That means every
  runtime.c helper reachable this way (`rt_fork`, the `rt_ptrace_*`
  family, byte-level file I/O, ...) takes pointer parameters and
  dereferences once, the same shape as a Fortran dummy argument — *not*
  the fixed-signature by-value convention the older I/O helpers
  (`rt_print_int`, ...) use. `GET_COMMAND_ARGUMENT`/`EXECUTE_COMMAND_LINE`
  additionally auto-inject the CHARACTER argument's compile-time-known
  length as a hidden extra argument, since our buffers are space-padded
  with no null terminator and the user never writes that length by hand.
- **Non-PIE Linux executables by default** (`target.py`: `-no-pie`). Not
  required for the compiler itself, but it's what makes a disassembler's
  or `nm`/`readelf`'s static addresses directly usable by the ptrace-based
  debugger with no ASLR-base bookkeeping — the same reason gdb defaults to
  disabling ASLR for a debuggee, just done at link time here instead of at
  attach time. `rt_ptrace_traceme` also calls `personality(ADDR_NO_RANDOMIZE)`
  as a second line of defense.

## Toolchain: disassembler, debugger, terminal IDE — written in Fortran

`tools/` holds three programs written *in this project's own Fortran
subset* and compiled by `fortranc.py` like anything else: a disassembler,
a debugger, and a terminal IDE tying them together. Build them with
`tools/build_tools.sh` (writes to `tools/bin/`, gitignored).

Honest scope, stated up front:

- **`fortran_disasm.f90`** is a **disassembler** (machine code → assembly
  text), not a decompiler (assembly → structured high-level source) —
  true decompilation (control-flow and type recovery) is a much larger
  undertaking than fits here. It parses the ELF64 header and program
  headers itself (to locate the segment containing a given virtual
  address — no section-header/string-table lookup needed, so no general
  string search was required to build it) and decodes a practical subset
  of x86-64: the instructions this project's own codegen.py actually
  emits (integer ALU/stack ops, SSE2 scalar-double arithmetic, jumps/
  calls, common addressing forms including RIP-relative and SIB
  scale-index-base). Unrecognized opcodes are reported and skipped a byte
  at a time rather than aborting the whole listing.
  ```
  tools/bin/fortran_disasm <executable> [start-vaddr-decimal]
  ```
  Defaults to the ELF entry point (`_start`, glibc's, not yours); pass
  `main`'s address (e.g. from `readelf -s`) to see your own code.
- **`fortran_dbg.f90`** is a real **ptrace-based debugger** (Linux only —
  ptrace has no Windows equivalent): forks, `PTRACE_TRACEME`s, `execve`s
  the target, sets a breakpoint by patching a byte to `0xCC`, continues,
  catches the resulting `SIGTRAP`, dumps `rip/rax/rsp/rbp/rdi/rsi`,
  restores the original byte, single-steps a few instructions, then runs
  to completion and reports the exit code.
  ```
  tools/bin/fortran_dbg <executable> [breakpoint-vaddr-decimal]
  ```
- **`fortran_ide.f90`** is a **terminal UI**, not a windowed GUI — this
  Fortran subset has no graphics FFI (no BIND(C) interface to a windowing
  library), so a text menu is the honest deliverable. It still drives the
  whole toolchain interactively: view source, compile (shells out to
  `fortranc.py` via `EXECUTE_COMMAND_LINE`), run, disassemble, and debug
  (prompts for a breakpoint address, then invokes `fortran_dbg`).
  ```
  tools/bin/fortran_ide <source.f90>
  ```
  Its shell-out paths are hardcoded to this repository's location
  (`/home/user/HAMIVTZAR/fortran_compiler/...`) — a real limitation if you
  move the checkout, noted rather than silently broken.

These were also where two real, if narrow, gaps in the compiler itself
turned up and got fixed along the way: passing more than the
register-argument count of arguments to a user procedure previously
dropped the extras silently on the floor instead of spilling them to the
stack (`many_args.f90` regression-tests this now), and the Windows
target's callee-side offset for a spilled argument didn't originally
account for the 32-byte shadow space.

Tests: `tests/test_tools.py` compiles all three and drives them against a
compiled example — the debugger test skips itself if ptrace isn't
permitted in the sandbox it's run in, rather than failing.

## Examples

See `examples/`: `hello.f90`, `factorial.f90`, `fibonacci.f90`,
`ifelse.f90` (FizzBuzz), `arrays.f90`, `subprograms.f90` (subroutine +
function, argument mutation), `bubble_sort.f90` (array argument, in-place
mutation), `matmul.f90` (2-D arrays), `primes.f90` (sieve of Eratosthenes,
`PARAMETER`), `rk4_ode.f90` (generic Runge-Kutta ODE solver taking the
derivative as a procedure argument), `recursive_factorial.f90`,
`many_args.f90` (9-argument call, exercises stack-spilled arguments on
both targets).

See also `tools/` (disassembler, debugger, terminal IDE — described above).

## Tests

```
pip install pytest
python3 -m pytest fortran_compiler/tests -q
```

`test_compiler.py` compiles and runs every example for the Linux target
natively, and for the Windows target under Wine if `wine64` is installed
(skipped otherwise). `test_tools.py` compiles the disassembler/debugger/IDE
and drives each against a compiled example (the debugger test skips itself
if ptrace isn't permitted in the sandbox).
