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
- Intrinsics: `SQRT ABS MOD INT REAL DBLE MAX MIN SIN COS TAN EXP LOG
  FLOOR CEILING NINT SIGN`
- Arguments are passed by reference, matching Fortran semantics, so
  subroutines can mutate their arguments (`CALL swap(a, b)` works)

Not supported: `MODULE`s, derived types, `CHARACTER` variables (string
*literals* work fine in `PRINT`), allocatable/pointer attributes, formatted
`PRINT`/`FORMAT` strings, `GOTO` and statement labels, internal procedures,
the standalone F77-style `PARAMETER (name = value)` statement (use
`TYPE, PARAMETER ::` instead).

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

## Examples

See `examples/`: `hello.f90`, `factorial.f90`, `fibonacci.f90`,
`ifelse.f90` (FizzBuzz), `arrays.f90`, `subprograms.f90` (subroutine +
function, argument mutation), `bubble_sort.f90` (array argument, in-place
mutation), `matmul.f90` (2-D arrays), `primes.f90` (sieve of Eratosthenes,
`PARAMETER`).

## Tests

```
pip install pytest
python3 -m pytest fortran_compiler/tests -q
```

Compiles and runs every example for the Linux target natively, and for the
Windows target under Wine if `wine64` is installed (skipped otherwise).
