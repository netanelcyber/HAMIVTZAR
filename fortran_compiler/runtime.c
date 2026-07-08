/* Minimal I/O runtime linked into every program the Fortran-subset compiler
 * produces. Compiled unchanged by both native gcc (Linux target) and
 * x86_64-w64-mingw32-gcc (Windows target) -- it is plain, portable C, so the
 * front end/codegen (the actual "Fortran compiler" part of this project)
 * never has to deal with libc's variadic-call ABI directly: each helper here
 * has a fixed, simple signature that the generated assembly calls directly.
 *
 * Written against C23 (built via -std=c2x: GCC 13 knows the standard by that
 * spelling, `c23` arriving only in GCC 14+) so it already speaks the
 * direction the next revision (informally "C2y"/"C29") continues: `bool`/
 * `true`/`false`/`nullptr` as keywords rather than <stdbool.h> macros, and
 * `constexpr` for values that are genuinely compile-time constants.
 */
#include <stdio.h>
#include <stdlib.h>

constexpr long IPOW_INVALID_EXPONENT_RESULT = 0;

void rt_print_int(long v) {
    printf("%ld", v);
}

void rt_print_logical(long v) {
    fputc(v ? 'T' : 'F', stdout);
}

[[noreturn]] void rt_exit(void) {
    fflush(stdout);
    exit(0);
}

void rt_print_real(double v) {
    printf("%g", v);
}

void rt_print_str(const char *s, long len) {
    if (s == nullptr || len <= 0) return;
    fwrite(s, 1, (size_t)len, stdout);
}

void rt_print_space(void) {
    fputc(' ', stdout);
}

void rt_print_newline(void) {
    fputc('\n', stdout);
}

[[nodiscard]] long rt_read_int(void) {
    long v = 0;
    if (scanf("%ld", &v) != 1) return 0;
    return v;
}

[[nodiscard]] double rt_read_real(void) {
    double v = 0.0;
    if (scanf("%lf", &v) != 1) return 0.0;
    return v;
}

[[nodiscard]] long rt_ipow(long base, long exp) {
    if (exp < 0) return IPOW_INVALID_EXPONENT_RESULT;
    long result = 1;
    bool done = exp == 0;
    while (!done) {
        if (exp & 1) result *= base;
        base *= base;
        exp >>= 1;
        done = exp == 0;
    }
    return result;
}
