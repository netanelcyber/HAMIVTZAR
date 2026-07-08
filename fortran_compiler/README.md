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
- Types: `INTEGER`, `REAL`/`DOUBLE PRECISION` (both 64-bit), `LOGICAL`; 1-D
  arrays with a literal-integer extent (`INTEGER :: a(10)`)
- Expressions: `+ - * / **`, unary `+/-`, relational (`.EQ./==` etc.),
  logical (`.AND. .OR. .NOT. .EQV. .NEQV.`), with INTEGER/REAL promotion
- Statements: assignment, `PRINT *`/`WRITE(*,*)`, `READ *`/`READ(*,*)`,
  block `IF/THEN/ELSE IF/ELSE/END IF` (and single-line `IF (...) stmt`),
  `DO var = a,b[,c]` / `DO WHILE (...)`, `EXIT`, `CYCLE`, `CALL`, `RETURN`,
  `STOP`
- Intrinsics: `SQRT ABS MOD INT REAL DBLE MAX MIN SIN COS TAN EXP LOG`
- Arguments are passed by reference, matching Fortran semantics, so
  subroutines can mutate their arguments (`CALL swap(a, b)` works)

Not supported: `MODULE`s, derived types, multi-dimensional arrays,
allocatable/pointer attributes, formatted `PRINT`/`FORMAT` strings, `GOTO`
and statement labels, internal procedures, array-valued arguments.

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
  (Windows).

## Examples

See `examples/`: `hello.f90`, `factorial.f90`, `fibonacci.f90`,
`ifelse.f90` (FizzBuzz), `arrays.f90`, `subprograms.f90` (subroutine +
function, argument mutation).

## Tests

```
pip install pytest
python3 -m pytest fortran_compiler/tests -q
```

Compiles and runs every example for the Linux target natively, and for the
Windows target under Wine if `wine64` is installed (skipped otherwise).
