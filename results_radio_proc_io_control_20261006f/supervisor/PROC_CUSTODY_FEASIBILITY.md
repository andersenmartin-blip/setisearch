# F direct-child counter observation — source-only preparation

Prepared 6 October 2026, outside the frozen C/D/E sources and actual roots.
This draft does not authorize or dispatch F. It imports no scientific package,
launches no installed interpreter or actual child, and opens no spectrum.

## Concrete gap and useful operation

The prior local PID observer correctly refused this environment: the Python
wait namespace and the visible proc mount use different PID numbers. The
observed self chain had two elements (outer proc PID, local `getpid()`), whereas
`/proc/<local getpid()>` identified an unrelated process. `wait4` still owns the
direct child in the local namespace. This is a mapping problem that can be
addressed without ptrace, a new guard, native package imports or a loader replay.

The proposed single harmless F control is base Python `-I -B -S`, under the
unchanged guard/seal/phase2 binaries. It sleeps initially for a bounded 0.25 s,
reads a frozen deterministic 131,072-byte payload eight times (1,048,576
workload bytes), and reports its own before/after proc IO and exact workload
hash. Root owns its separate admission/freeze, payload, driver, guard dispatch,
outer lifetime and final evidence checks. The parent observer must establish
the real direct-child identity and read the retained zombie IO before `wait4`.
The parent can then compare observed `rchar` against both the leaf's self
report and the independently frozen workload minimum.

## Observer contract

`proc_custody.py` provides `Budget`, `ProcFS`, `resolve_child`, `snapshot`,
`terminal_observation`, and `owner_description`. `leaf_supervisor_F.py` retains
the E `run_leaf(argv, env, cwd, outputprefix, limits, global_deadline)` signature
and exact limit-key set. Root injects the independently pinned `proc_custody`
module before loading the supervisor. Neither module starts a child at import.

The proc root, numeric owner directory and numeric child directory are held
open. The owner's first/last `NSpid` elements bind outer proc `Pid` to local
`getpid()`; its held directory, starttime, namespace inode, single-thread
identity, selected UID fields and effective capabilities are checked. All four
UID fields must equal the current owner UID. Owner/root identity is checked
again through resolution and on both sides of each snapshot.

The resolver first reads the held proc view's
`self/task/<outer owner TID>/children`. An unavailable children file permits
one bounded proc enumeration. Each candidate is charged and checked for
numeric-directory `Pid == Tgid`, matching first/last PID-chain elements and
depth, outer `PPid`, held namespace identity, owner UID and stable starttime.
Every rejected candidate remains charged. Absence/ambiguity refuses.
Identity drift after a candidate matched refuses the whole resolution. A
scheduler state change alone does not imply PID reuse.

Snapshots read `status`, `stat` and `io` through the held child directory,
checking identity before and after the IO read and against the named directory.
`terminal_observation` first calls `waitid(P_PID, local_child,
WEXITED|WNOHANG|WNOWAIT)`, requires the exact exited/killed/dumped child, then
requires zombie state through the snapshot. It never reaps. The supervisor
keeps its mandatory `wait4` path even when observation fails. Missing counters
are `None`; actual zero counters remain present integers.

Read bytes, operations, candidate counts, rejected candidates and errors are
bounded and reported. Close operations always close their descriptors even
when accounting refuses, and a closed bound handle is marked closed before
any further cleanup. The supervisor charges all proc reads to the parent;
`proc_child_metadata_read_charge_bytes` is deliberately `None`, because path
names do not establish a separately measured child-only subset.

The interpreter wrapper function is byte-identical to E, SHA256
`165d7cfb047f0b32482c379f10a132fa2570f9e07837383da90934c3ebcb883c`.
It already accepts `-S`; no wrapping change is needed.

## Prospective ceilings and validation

Root's proposed envelope is parent 30 s, active operation 20 s, leaf 10 s,
CPU 5 s, parent AS 256 MiB, leaf AS 128 MiB, artifacts 16 MiB, terminal
publication 1 MiB, parent explicit reads 512 MiB, opaque child reserve 16 MiB
and joined reads 528 MiB. The supervisor receives explicit 32 MiB pin-read and
16 MiB proc-read ceilings, sampling 0.02 s and cleanup 2 s. Its observer also
caps 65,536 metadata operations and 1,024 candidates. Root's actual frozen
limit document, rather than this draft description, controls admission.

Nineteen offline resolver/snapshot tests cover namespace depth/indices,
wrong direct inner-PID paths, owner UID/starttime, namespace/parent mismatch,
ambiguity, scan/read ceilings, PID reuse, held/name/root drift, state-only
transitions, close refusal, missing versus zero IO and WNOWAIT ownership.
Five fake-supervisor tests cover success, missing terminal IO, child identity
drift, nonzero exit and repeated selector failure after dispatch; each verifies
one fake dispatch, WNOWAIT before one
fake `wait4`, retained streams/JSON and descriptor cleanup. No actual process
was created by these fixtures. Logs are retained beside their source.
The first selector-failure fixture incorrectly required authenticated guard
readiness despite refusing every stream read. Its failed log is retained as
`leaf-supervisor-F-fixture-adjustment-failure.log`; the corrected assertion
requires a failed guard status and still requires terminal sampling/reaping.

## Terminal PID namespace semantics

Primary upstream implementation distinguishes `/proc/<pid>/ns/pid` from
`pid_for_children`: [`pidns_get` in kernel/pid_namespace.c](https://github.com/torvalds/linux/blob/master/kernel/pid_namespace.c)
uses `task_active_pid_ns`; `pidns_for_children_get` instead depends on
`task->nsproxy`. [`task_active_pid_ns` in kernel/pid.c](https://github.com/torvalds/linux/blob/master/kernel/pid.c)
uses the task's attached PID. The
[`WNOWAIT` branch of `wait_task_zombie`](https://kernel.googlesource.com/pub/scm/linux/kernel/git/stable/linux-stable/%2B/11af27f494086188620e7768e421894af93c126a/kernel/exit.c)
returns without transitioning the zombie to dead/releasing its task. The
[wait manual](https://man7.org/linux/man-pages/man2/wait.2.html) likewise
specifies that WNOWAIT keeps the child waitable. Together these support the
inference that the unreaped zombie's active `ns/pid` remains available;
`ns/pid_for_children` is not used by this observer.

This is an implementation-based expectation, not a probe of an unfrozen child
or an attestation of the running kernel's exact source. Exact v6.18 source URL
opens were unavailable through the search service; the retrieved primary
upstream functions and stable WNOWAIT branch support this design. Permission
or mount restrictions can still refuse the terminal namespace lookup, yielding
missing counter evidence and a failed observation while the supervisor reaps.

## Limits and next original-contract work

This is direct-child kernel-counter and identity evidence. It is not
continuous loader/path custody, a complete independent native graph, a full
native IO qualification, a hosted calibration/evaluation profile, codec
qualification or scientific admission. Holding namespace/root/directory
identities does not certify continuous namespace or mount closure.

The current guard denies ptrace, cross-process memory reads and further
seccomp calls. Although kernel/header metadata advertise seccomp user
notification, a broker would require a new guard and new FD/pointer-custody
law; its actual usability has not been established. LD_AUDIT names/link-map
events likewise do not produce complete FD/byte custody. Neither is needed
for this smaller counter observation.

The independently retained `AUTHORITATIVE_GATE_AUDIT.md` binds the original
scientific validators at immutable commit
`6da771e78667f0746e87d05915c6feb683541a25`. Those validators require an
independently complete five-role execution/native inventory, resolved graph,
authentic joined profiles and bounded physical lifetime; they do not prescribe
procfs, syscall tracing or continuous namespace accounting. F is evidence for
one concrete gap. Subsequent source-shaped full16-row codec/normalization
work may be prepared under its own new bounded scope, with controlled
provenance and all scientific fields still pending.
