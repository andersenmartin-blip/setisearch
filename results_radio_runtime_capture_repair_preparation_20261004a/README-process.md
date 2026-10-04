# Prospective process-attribution repair — 4 October 2026

This source-only preparation repairs the process-selection defect in the closed
metadata capture. It creates no live contract, activation, allocation or runtime
capture. The original source namespace, spent marker, eight original output
members and their recorded failure remain unchanged. The selected engineering
subtotal stays **970 seconds / 48 MiB**; all eleven scientific admission inputs
remain pending.

## Preserved defect and regression

The original matcher searched visible `/proc` entries and accepted the first
record whose numeric `NSpid` tail equalled `Popen.pid`. Each of the three retained
samples selected the unrelated `caas-prefix-tra` process: proc-visible PID 6,
PPid 1, session 0, starttime 139. Those records do not establish collector RSS or
collector group membership.

`process-regression-before-repair-01.log` preserves the meaningful failing
regression against the original matcher: the assertion that a bare numeric PID
must be refused failed. Its exact gate and test sources are retained in
`process-regression-before-repair-01/`. The repaired regression reads all three
original sample bodies and rejects them. The original sample file is read only.

The second development run exposed deadline classification: a sampling deadline
was reported as a supervisor exception instead of `CHILD_DEADLINE`. The exact
then-current source and tests are retained in `process-development-failure-02/`,
with the raw `process-development-tests-02.log`. No historical failure is erased.

A final review found that malformed pidfd fdinfo fields could lose raw bytes
already returned before parsing failed. The new pure regression failed against
that version; its exact gate/test cohort is retained in
`process-development-failure-08/` with `process-development-tests-08.log`. The
repair now records the bounded most recent fdinfo bytes before parsing them.

## Kernel-bound identity

The isolated, single-thread parent opens a pidfd for its direct child before any
wait/reap. `waitid(P_PIDFD, WNOHANG | WNOWAIT | WEXITED)` checks kernel wait
ownership without consuming the subsequent `wait4` resource receipt. The pidfd
object remains held, its device/inode token is checked, and sampling refuses a
closed or reaped handle.

The parent resolves its own proc-visible ID through the kernel `/proc/self`
link. Held parent/proc/fdinfo/PID-namespace descriptors then support a direct
pidfd `fdinfo` read. Its `Pid` identifies the child in the proc mount's namespace;
its complete `NSpid` vector must agree with the child status and the known local
child PID. This works in the current environment, where `/proc` shows host IDs
while `Popen` and `wait4` use nested namespace IDs. There is no numeric-tail
search or guessed mapping.

Every admitted sample additionally requires:

- the held/named child proc directory to agree;
- the child PID namespace inode to equal the held parent namespace inode;
- status/stat PPid to equal the authenticated proc-visible parent;
- stat session/group to equal the child proc-visible PID, and complete
  `NSsid`/`NSpgid` vectors to equal its `NSpid` vector;
- one selected child thread and a starttime that does not predate the parent;
- stable starttime, namespace, parent, group, session and executable identities;
- the child `exe` inode to equal the inode from the **same held interpreter read
  whose bytes passed the prelaunch size/hash/mode verification**.

The last requirement addresses a separate review finding: taking a fresh
`stat(python_path)` after byte verification could adopt a substituted, unverified
inode. The repaired gate passes the exact verified-read object token to the
child observer; it does not reread the native binary or manufacture authority
from a later pathname lookup. A regression replaces a synthetic file with
identical bytes but a different inode and proves that the new inode is refused.

Status/stat, pidfd fdinfo and selected identity checks bracket each successful
sample. The previous identity must remain equal. Missing, duplicate, malformed,
unreadable, terminal, mismatched or unprovable identity closes the engineering
attempt. A reaped numeric PID is never signalled or rebound; the direct child is
also targeted through `pidfd_send_signal` during bounded termination.

## Finite observations and retained evidence

All proc record bytes pass through the joined read accounting, including bytes
received in a refused over-cap or exhausted-budget read. Proc records have a
16 KiB cap. Visible process enumeration stops above 4096 numeric entries and
checks the child deadline during enumeration and each record observation.

Raw parent status/stat and initial/terminal pidfd fdinfo records are retained in
the attribution receipt. Successful samples retain both child status/stat
observations, both pidfd fdinfo observations, and raw stat records from the
bounded visible process snapshot. A partial failed sample/read preserves the
bytes actually received and its error; unavailable visible records are explicit.
An incomplete membership snapshot cannot produce a positive metadata outcome.
The positive state requires at least the initial authenticated live sample.

These are bounded visible snapshots, **not an aggregate descendant-absence or
full-lifetime RSS certificate**. Processes may exist between samples, outside the
visible proc mount or outside the selected group. VmRSS/VmHWM are selected Linux
observations, and `wait4` remains the direct-child resource receipt. The parent
lifetime RSS point is not promoted to a complete program peak.

All held descriptors close on success or failure. Child deadlines, bounded
kill/reap, raw-stream caps, source before/after guards, joined read reservation,
the fixed eight-member output scope and irreversible one-child/spent law remain
in force. A failure before ordinary pipe draining preserves the received stream
prefix; it does not certify that an unread pipe contained no additional bytes.

## Validation and authorization boundary

The final process suite has **45 tests**, run with the selected primary Python
under `-I -B -S`; `process-final-tests-09.log` is the final retained producer log.
Tests use pure byte fixtures or disjoint tiny synthetic Python children. They
cover the exact three historical collisions, same/cross proc namespace mappings,
PID reuse, parent/session/group/namespace/thread/executable mismatches, ambiguous
and missing fields, descriptor closure, post-reap refusal, read caps, deadline,
visible membership refusal, descendant detection, raw streams, source drift,
publication/activation refusal and the permanent spent guard.

Python's standard-library process functions and Linux syscalls run inside the
selected primary interpreter. This does not mean that the interpreter has no
native runtime. No NumPy, h5py, hdf5plugin, HDF5/plugin binary, scientific dataset
or actual collector is imported or executed by these tests; no native binary
inspection helper is invoked.

The inherited v1 marker/path and public API guard remain unchanged in this
limited inert repair. The closed activation path cannot authorize a successor.
A future actual capture needs a fresh namespace/path, a complete new contract
integration and immutable full freeze/readback, plus a separately recorded
irreversible allocation. This preparation supplies none of those inputs and
does not qualify source closure, native runtime, CAS or scientific execution.

## Primary sources checked

- [Linux pidfd_open(2)](https://man7.org/linux/man-pages/man2/pidfd_open.2.html):
  direct unreaped-child pidfd ownership, zombie/reap conditions and descriptor
  lifetime; the implementation uses exclusive default SIGCHLD ownership and
  kernel `waitid(P_PIDFD)` rather than assuming a numeric PID stays valid.
- [Linux kernel pidfd fdinfo implementation](https://github.com/torvalds/linux/blob/master/fs/pidfs.c):
  `Pid`/`NSpid` are relative to the procfs instance, and terminal/no-visible-task
  values cannot be accepted as a live child identity.
- [Linux proc documentation](https://docs.kernel.org/filesystems/proc.html):
  held proc descriptors do not switch to a newly reused PID; status namespace
  vectors and stat parent/group/session/starttime semantics; RSS precision limits.
- [Python 3.12 os documentation](https://docs.python.org/3.12/library/os.html):
  `pidfd_open`, `waitid(P_PIDFD)`/`WNOWAIT` and `wait4` interfaces.
