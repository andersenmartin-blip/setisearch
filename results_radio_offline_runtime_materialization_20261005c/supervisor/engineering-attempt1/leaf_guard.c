#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <sys/prctl.h>
#include <sys/ptrace.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <unistd.h>

#if !defined(__x86_64__) || !defined(SYS_execveat)
#error "This frozen guard requires Linux x86_64 with execveat"
#endif

#define DENY(n) BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, (n), 0, 1), \
                BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM)
#define TRACE_EXEC(n) BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, (n), 0, 1), \
                BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_TRACE)

extern char **environ;

static void fail(const char *message) {
    dprintf(STDERR_FILENO, "leaf_guard_refused:%s:errno=%d\n", message, errno);
    _exit(125);
}

static unsigned long long number(const char *text) {
    char *end = NULL;
    errno = 0;
    unsigned long long value = strtoull(text, &end, 10);
    if (errno || !text[0] || text[0] == '-' || !end || *end) fail("invalid_number");
    return value;
}

static void ceiling(int kind, unsigned long long value) {
    struct rlimit limit = {(rlim_t)value, (rlim_t)value};
    if ((unsigned long long)limit.rlim_cur != value || setrlimit(kind, &limit))
        fail("rlimit");
}

int main(int argc, char **argv) {
    /* The supervisor hashes already-open descriptors before spawning this
       guard. Those stable descriptors avoid pathname replacement at handoff. */
    if (argc < 11 || strcmp(argv[1], "--python-fd") ||
        strcmp(argv[3], "--status-fd") || strcmp(argv[5], "--address-space") ||
        strcmp(argv[7], "--cpu-seconds") || strcmp(argv[9], "--file-bytes"))
        fail("arguments");
    int python_fd = (int)number(argv[2]);
    int status_fd = (int)number(argv[4]);
    if (argc < 15 || strcmp(argv[11], "--guard-fd") || strcmp(argv[13], "--") ||
        python_fd < 3 || status_fd < 3 ||
        python_fd == status_fd) fail("descriptor_or_argv");
    int guard_fd = (int)number(argv[12]);
    if (guard_fd < 3 || guard_fd == python_fd || guard_fd == status_fd || close(guard_fd))
        fail("guard_descriptor_close");
    ceiling(RLIMIT_AS, number(argv[6]));
    ceiling(RLIMIT_CPU, number(argv[8]));
    ceiling(RLIMIT_FSIZE, number(argv[10]));
    ceiling(RLIMIT_CORE, 0);
    if (fcntl(python_fd, F_SETFD, FD_CLOEXEC) ||
        fcntl(status_fd, F_SETFD, FD_CLOEXEC)) fail("cloexec");
    if (ptrace(PTRACE_TRACEME, 0, NULL, NULL)) fail("ptrace_required");
    if (raise(SIGSTOP)) fail("initial_stop");
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) fail("no_new_privs");
    struct sock_filter filters[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        BPF_JUMP(BPF_JMP | BPF_JSET | BPF_K, 0x40000000U, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
        DENY(SYS_fork), DENY(SYS_vfork), DENY(SYS_clone), DENY(SYS_clone3),
        DENY(SYS_socket), DENY(SYS_socketpair), DENY(SYS_connect),
        DENY(SYS_bind), DENY(SYS_listen), DENY(SYS_accept), DENY(SYS_accept4),
        DENY(SYS_sendto), DENY(SYS_sendmsg), DENY(SYS_sendmmsg),
        DENY(SYS_recvfrom), DENY(SYS_recvmsg), DENY(SYS_recvmmsg),
        DENY(SYS_shutdown), DENY(SYS_getsockname), DENY(SYS_getpeername),
        DENY(SYS_setsockopt), DENY(SYS_getsockopt),
        DENY(SYS_io_uring_setup), DENY(SYS_io_uring_enter), DENY(SYS_io_uring_register),
        DENY(SYS_io_setup), DENY(SYS_io_destroy), DENY(SYS_io_submit),
        DENY(SYS_io_cancel), DENY(SYS_io_getevents), DENY(SYS_io_pgetevents),
        DENY(SYS_ptrace), DENY(SYS_seccomp), DENY(SYS_unshare), DENY(SYS_setns),
        DENY(SYS_process_vm_readv), DENY(SYS_process_vm_writev),
        TRACE_EXEC(SYS_execve), TRACE_EXEC(SYS_execveat),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    };
    struct sock_fprog program = {
        .len = (unsigned short)(sizeof(filters) / sizeof(filters[0])),
        .filter = filters,
    };
    if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program)) fail("seccomp_required");
    int nnp = prctl(PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0);
    int filter = prctl(PR_GET_SECCOMP, 0, 0, 0, 0);
    if (nnp != 1 || filter != SECCOMP_MODE_FILTER) fail("filter_status");
    if (dprintf(status_fd,
        "{\"schema\":\"radio-leaf-guard-v1\",\"no_new_privs\":1,"
        "\"seccomp_mode\":2,\"descendants_denied\":true,\"sockets_denied\":true,"
        "\"async_io_denied\":true,\"exec_trace_required\":true}\n") < 0)
        fail("status_write");
    /* No exec fallback: the supervisor admits this sole trace event. The
       surviving filter traps every later exec, which the supervisor refuses. */
    syscall(SYS_execveat, python_fd, "", &argv[14], environ, AT_EMPTY_PATH);
    fail("pinned_python_exec");
}
