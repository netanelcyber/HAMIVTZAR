/* Minimal I/O runtime linked into every program the Fortran-subset compiler
 * produces. Compiled unchanged by both native gcc (Linux target) and
 * x86_64-w64-mingw32-gcc (Windows target) -- it is plain, portable C, so the
 * front end/codegen (the actual "Fortran compiler" part of this project)
 * never has to deal with libc's variadic-call ABI directly: each helper here
 * has a fixed, simple signature that the generated assembly calls directly.
 */
#include <stdio.h>
#include <stdlib.h>

void rt_print_int(long v) {
    printf("%ld", v);
}

void rt_print_logical(long v) {
    fputc(v ? 'T' : 'F', stdout);
}

void rt_exit(void) {
    fflush(stdout);
    exit(0);
}

void rt_print_real(double v) {
    printf("%g", v);
}

void rt_print_str(const char *s, long len) {
    fwrite(s, 1, (size_t)len, stdout);
}

void rt_print_space(void) {
    fputc(' ', stdout);
}

void rt_print_newline(void) {
    fputc('\n', stdout);
}

long rt_read_int(void) {
    long v = 0;
    if (scanf("%ld", &v) != 1) return 0;
    return v;
}

double rt_read_real(void) {
    double v = 0.0;
    if (scanf("%lf", &v) != 1) return 0.0;
    return v;
}

long rt_ipow(long base, long exp) {
    long result = 1;
    if (exp < 0) return 0;
    while (exp > 0) {
        if (exp & 1) result *= base;
        base *= base;
        exp >>= 1;
    }
    return result;
}
