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
#include <string.h>
#include <stddef.h>

#if defined(__linux__) || defined(__unix__)
#define RT_HAVE_PTRACE 1
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <sys/user.h>
#include <sys/personality.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#endif

constexpr long IPOW_INVALID_EXPONENT_RESULT = 0;

/* Helpers below this point follow ordinary Fortran-to-Fortran by-reference
 * argument passing (codegen.py's `_emit_user_call`, same as any user
 * SUBROUTINE/FUNCTION call) rather than the fixed by-value signatures
 * above: every parameter here is a pointer, dereferenced once. A CHARACTER
 * actual argument arrives as a raw buffer pointer (fixed-length,
 * space-padded, no null terminator) exactly like a Fortran array argument
 * -- there's no separate "string" representation. */

constexpr long RT_MAX_FILES = 64;
static FILE *g_files[RT_MAX_FILES];

static void rt_copy_padded_cstr(const char *buf, long buflen, char *out, long outcap) {
    long n = buflen < outcap - 1 ? buflen : outcap - 1;
    while (n > 0 && buf[n - 1] == ' ') n--;
    memcpy(out, buf, (size_t)n);
    out[n] = '\0';
}

/* ---- command-line arguments / EXECUTE_COMMAND_LINE ---- */

static long g_argc = 0;
static char **g_argv = nullptr;

void rt_save_args(long argc, char **argv) {
    g_argc = argc;
    g_argv = argv;
}

[[nodiscard]] long rt_command_argument_count(void) {
    return g_argc > 0 ? g_argc - 1 : 0;
}

void rt_get_command_argument(long *index, char *buf, long *buflen) {
    long idx = *index;
    long n = *buflen;
    for (long i = 0; i < n; i++) buf[i] = ' ';
    if (idx < 0 || idx >= g_argc) return;
    const char *s = g_argv[idx];
    long len = 0;
    while (s[len] != '\0' && len < n) { buf[len] = s[len]; len++; }
}

void rt_execute_command_line(const char *cmd, long *cmdlen) {
    char tmp[4096];
    rt_copy_padded_cstr(cmd, *cmdlen, tmp, (long)sizeof(tmp));
    fflush(stdout);
    system(tmp);
}

/* ---- byte-level file I/O ---- */

[[nodiscard]] long rt_open_read(const char *name, long *namelen) {
    char tmp[4096];
    rt_copy_padded_cstr(name, *namelen, tmp, (long)sizeof(tmp));
    FILE *f = fopen(tmp, "rb");
    if (!f) return -1;
    for (long i = 0; i < RT_MAX_FILES; i++) {
        if (!g_files[i]) { g_files[i] = f; return i; }
    }
    fclose(f);
    return -1;
}

[[nodiscard]] long rt_open_write(const char *name, long *namelen) {
    char tmp[4096];
    rt_copy_padded_cstr(name, *namelen, tmp, (long)sizeof(tmp));
    FILE *f = fopen(tmp, "wb");
    if (!f) return -1;
    for (long i = 0; i < RT_MAX_FILES; i++) {
        if (!g_files[i]) { g_files[i] = f; return i; }
    }
    fclose(f);
    return -1;
}

void rt_close(long *handle) {
    long h = *handle;
    if (h < 0 || h >= RT_MAX_FILES || !g_files[h]) return;
    fclose(g_files[h]);
    g_files[h] = nullptr;
}

/* -1 at EOF or on a bad handle, else the byte value 0..255 */
[[nodiscard]] long rt_read_byte(long *handle) {
    long h = *handle;
    if (h < 0 || h >= RT_MAX_FILES || !g_files[h]) return -1;
    int c = fgetc(g_files[h]);
    return c == EOF ? -1 : (long)c;
}

void rt_write_byte(long *handle, long *byteval) {
    long h = *handle;
    if (h < 0 || h >= RT_MAX_FILES || !g_files[h]) return;
    fputc((int)(*byteval & 0xff), g_files[h]);
}

[[nodiscard]] long rt_file_size(const char *name, long *namelen) {
    char tmp[4096];
    rt_copy_padded_cstr(name, *namelen, tmp, (long)sizeof(tmp));
    FILE *f = fopen(tmp, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fclose(f);
    return sz;
}

void rt_print_char(long *byteval) {
    fputc((int)(*byteval & 0xff), stdout);
}

/* Trims trailing blanks off `src`, drops a trailing ".f90"/".F90"
 * extension if present, and appends ".out" -- used by the terminal IDE
 * to name a compiled executable after its source file. Doing this in C
 * sidesteps needing general TRIM/substring support in the Fortran
 * CHARACTER subset (deliberately not implemented; see README). */
void rt_make_exe_name(const char *src, long *srclen, char *out, long *outlen) {
    long n = *srclen;
    while (n > 0 && src[n - 1] == ' ') n--;
    if (n > 4 && src[n - 4] == '.' &&
        (src[n - 3] == 'f' || src[n - 3] == 'F') && src[n - 2] == '9' && src[n - 1] == '0') {
        n -= 4;
    }
    long outcap = *outlen;
    for (long i = 0; i < outcap; i++) out[i] = ' ';
    long m = n < outcap ? n : outcap;
    memcpy(out, src, (size_t)m);
    const char *suffix = ".out";
    for (long i = 0; i < 4 && m + i < outcap; i++) out[m + i] = suffix[i];
}

void rt_int_to_str(long *value, char *buf, long *buflen) {
    long n = *buflen;
    for (long i = 0; i < n; i++) buf[i] = ' ';
    char tmp[32];
    int len = snprintf(tmp, sizeof(tmp), "%ld", *value);
    if (len < 0) len = 0;
    if (len > (int)n) len = (int)n;
    memcpy(buf, tmp, (size_t)len);
}

[[nodiscard]] long rt_parse_int(const char *buf, long *len) {
    long n = *len;
    long i = 0;
    while (i < n && buf[i] == ' ') i++;
    bool neg = i < n && buf[i] == '-';
    if (i < n && (buf[i] == '-' || buf[i] == '+')) i++;
    long v = 0;
    while (i < n && buf[i] >= '0' && buf[i] <= '9') {
        v = v * 10 + (buf[i] - '0');
        i++;
    }
    return neg ? -v : v;
}

/* ---- process control for the ptrace-based debugger (Linux only) ----
 * Everything below is a thin, single-purpose wrapper: one ptrace/wait
 * operation per function, matching the fixed-arity-by-reference calling
 * convention above. Non-Linux builds (the Windows target, still compiled
 * unchanged by mingw so the rest of the runtime keeps working there) get
 * stub versions that fail cleanly -- this is a Linux-only debugger by
 * nature (ptrace has no Windows equivalent), not a bug. */

#ifdef RT_HAVE_PTRACE

[[nodiscard]] long rt_fork(void) {
    return (long)fork();
}

void rt_ptrace_traceme(void) {
    /* Belt-and-suspenders alongside the compiler's own -no-pie default:
     * disables ASLR for this process too, so a statically-known address
     * (from the disassembler, nm, readelf, ...) is directly usable even
     * against a PIE binary someone points the debugger at. */
    personality(ADDR_NO_RANDOMIZE);
    ptrace(PTRACE_TRACEME, 0, nullptr, nullptr);
}

[[noreturn]] void rt_execve_self(const char *path, long *pathlen) {
    char tmp[4096];
    rt_copy_padded_cstr(path, *pathlen, tmp, (long)sizeof(tmp));
    char *argv[] = { tmp, nullptr };
    execv(tmp, argv);
    _exit(127);
}

[[nodiscard]] long rt_waitpid(long *pid) {
    int status = 0;
    waitpid((pid_t)*pid, &status, 0);
    return (long)status;
}

[[nodiscard]] long rt_wifexited(long *status)   { return WIFEXITED((int)*status)   ? 1 : 0; }
[[nodiscard]] long rt_wexitstatus(long *status) { return WEXITSTATUS((int)*status); }
[[nodiscard]] long rt_wifstopped(long *status)  { return WIFSTOPPED((int)*status)  ? 1 : 0; }
[[nodiscard]] long rt_wstopsig(long *status)    { return WSTOPSIG((int)*status); }

[[nodiscard]] long rt_ptrace_peektext(long *pid, long *addr) {
    errno = 0;
    return ptrace(PTRACE_PEEKTEXT, (pid_t)*pid, (void *)*addr, nullptr);
}

void rt_ptrace_poketext(long *pid, long *addr, long *data) {
    ptrace(PTRACE_POKETEXT, (pid_t)*pid, (void *)*addr, (void *)*data);
}

static long rt_getregs_field(long pid, size_t offset) {
    struct user_regs_struct regs;
    ptrace(PTRACE_GETREGS, (pid_t)pid, nullptr, &regs);
    return *(long long *)((char *)&regs + offset);
}

[[nodiscard]] long rt_ptrace_get_rip(long *pid) { return rt_getregs_field(*pid, offsetof(struct user_regs_struct, rip)); }
[[nodiscard]] long rt_ptrace_get_rax(long *pid) { return rt_getregs_field(*pid, offsetof(struct user_regs_struct, rax)); }
[[nodiscard]] long rt_ptrace_get_rsp(long *pid) { return rt_getregs_field(*pid, offsetof(struct user_regs_struct, rsp)); }
[[nodiscard]] long rt_ptrace_get_rbp(long *pid) { return rt_getregs_field(*pid, offsetof(struct user_regs_struct, rbp)); }
[[nodiscard]] long rt_ptrace_get_rdi(long *pid) { return rt_getregs_field(*pid, offsetof(struct user_regs_struct, rdi)); }
[[nodiscard]] long rt_ptrace_get_rsi(long *pid) { return rt_getregs_field(*pid, offsetof(struct user_regs_struct, rsi)); }

void rt_ptrace_set_rip(long *pid, long *value) {
    struct user_regs_struct regs;
    ptrace(PTRACE_GETREGS, (pid_t)*pid, nullptr, &regs);
    regs.rip = (unsigned long long)*value;
    ptrace(PTRACE_SETREGS, (pid_t)*pid, nullptr, &regs);
}

void rt_ptrace_cont(long *pid) {
    ptrace(PTRACE_CONT, (pid_t)*pid, nullptr, nullptr);
}

void rt_ptrace_singlestep(long *pid) {
    ptrace(PTRACE_SINGLESTEP, (pid_t)*pid, nullptr, nullptr);
}

void rt_ptrace_kill(long *pid) {
    kill((pid_t)*pid, SIGKILL);
}

void rt_dump_maps(long *pid) {
    char path[64];
    snprintf(path, sizeof(path), "/proc/%ld/maps", (long)*pid);
    FILE *f = fopen(path, "r");
    if (!f) { printf("(cannot open %s)\n", path); return; }
    char line[512];
    while (fgets(line, sizeof(line), f)) fputs(line, stdout);
    fclose(f);
}

#else  /* !RT_HAVE_PTRACE: Windows/other -- fail cleanly, don't build a debugger there */

[[nodiscard]] long rt_fork(void) { return -1; }
void rt_ptrace_traceme(void) {}
[[noreturn]] void rt_execve_self(const char *path, long *pathlen) { (void)path; (void)pathlen; exit(127); }
[[nodiscard]] long rt_waitpid(long *pid) { (void)pid; return -1; }
[[nodiscard]] long rt_wifexited(long *status) { (void)status; return 0; }
[[nodiscard]] long rt_wexitstatus(long *status) { (void)status; return -1; }
[[nodiscard]] long rt_wifstopped(long *status) { (void)status; return 0; }
[[nodiscard]] long rt_wstopsig(long *status) { (void)status; return -1; }
[[nodiscard]] long rt_ptrace_peektext(long *pid, long *addr) { (void)pid; (void)addr; return -1; }
void rt_ptrace_poketext(long *pid, long *addr, long *data) { (void)pid; (void)addr; (void)data; }
[[nodiscard]] long rt_ptrace_get_rip(long *pid) { (void)pid; return -1; }
[[nodiscard]] long rt_ptrace_get_rax(long *pid) { (void)pid; return -1; }
[[nodiscard]] long rt_ptrace_get_rsp(long *pid) { (void)pid; return -1; }
[[nodiscard]] long rt_ptrace_get_rbp(long *pid) { (void)pid; return -1; }
[[nodiscard]] long rt_ptrace_get_rdi(long *pid) { (void)pid; return -1; }
[[nodiscard]] long rt_ptrace_get_rsi(long *pid) { (void)pid; return -1; }
void rt_ptrace_set_rip(long *pid, long *value) { (void)pid; (void)value; }
void rt_ptrace_cont(long *pid) { (void)pid; }
void rt_ptrace_singlestep(long *pid) { (void)pid; }
void rt_ptrace_kill(long *pid) { (void)pid; }
void rt_dump_maps(long *pid) { (void)pid; }

#endif

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
