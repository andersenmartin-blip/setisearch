# Radio native v2 — descendant escape guard component

**Result: DESCENDANT_ESCAPE_GUARD_COMPONENT_VERIFIED_EXECUTION_BLOCKED.**
The dedicated Linux supervisor now installs `PR_SET_NO_NEW_PRIVS` and a bounded
classic-seccomp filter after fork and before every worker exec. The irreversible
filter is inherited across fork/exec and refuses PID/other namespace creation or
transition, `ptrace`, cross-process memory access, `clone3` and `io_uring_setup`.
Ordinary fork/vfork and clone without namespace flags remain available.

The existing subreaper evidence may mark its bounded descendant wait chain complete
only when the guarded root exits successfully and the sole `wait4` owner reaches
terminal `ECHILD`. Resource finalization now rejects a bare completion boolean: it
requires the exact guard scope, all three installation flags and the complete fixed
denied-operation list. Global process-tree qualification remains false because the
outer final-report writer, complete runtime/parent environment, immutable public
execution preread and broader kernel/procfs escape surface are not yet closed.

## Verification

The fresh x86-64 negative control entered seccomp mode 2 with no-new-privileges and
received `EPERM` from actual `unshare`, `setns`, `ptrace` and `clone3` syscalls. Its
subreaper reached terminal `ECHILD`; an independent parent observed the supervisor
receipt fsync and termination in **0.119 s** with **13.77 MiB** maximum individual
RSS. This is a tiny component control, not evidence for the full workload.

The adjacent seven-module suite passes **200 tests in 76.564 s**. A preceding
deliberately minimal parent-PATH run is retained as a failed control: it removed the
frozen Node executable and produced 86 setup errors plus one helper failure. The
successful rerun restored the actual frozen runtime search path; protected child
environments remain the exact minimal three-variable contract.

- [Prospective plan revision f](config/radio_native_v2_compact_eight_input_control_20261002f.plan.json)
- [Reproduction script](results_radio_native_v2_escape_guard_20261002a/verify_escape_guard.py)
- [Verification summary](results_radio_native_v2_escape_guard_20261002a/verification-summary.json)
- [Test summary](results_radio_native_v2_escape_guard_20261002a/final-test-summary.json)
- [Independent outer observation](results_radio_native_v2_escape_guard_20261002a/escape-guard-control-observation.json)
- [Guarded subreaper receipt](results_radio_native_v2_escape_guard_20261002a/escape-guard-control/subreaper-receipt.json)
- [Passing test log](results_radio_native_v2_escape_guard_20261002a/final-tests-stderr.log)
- [Retained failed-PATH log](results_radio_native_v2_escape_guard_20261002a/failed-path-test-stderr.log)

## Disposition and continuation

Plan revision `20261002f` remains `BLOCKED_PREPARATION_REVIEW` and explicitly records
that the guard contract is prepared while an actual observed workload wait chain is
still required. No maximum-size source, eight-input control, reservation, RNG,
native case or telescope spectrum was opened. All scientific and execution authority
stays false.

**Exact continuation:** complete and independently verify the activation-time
runtime plus parent-environment join, then publish and read back the immutable
execution preread and cover the outer final-report fsync/termination boundary. Only
after those joins may one fresh eight-input engineering resource control be
considered. HD189733 remains selected, HD1461 remains HOLD, and GJ724 remains reserve.
127/24 is NOT ACTIVATED; spectra and holdouts stay unopened, LS paused, CHEOPS UNSENT.
Consolidate 9 October without extension. No external messages were sent.
