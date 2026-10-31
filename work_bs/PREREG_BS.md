# BS: deterministic file-stability investigation

This is engineering diagnosis of the preserved BQ and BR file failures. It
does not rerun A04, combine incomplete executions, generate powers, calculate
scan scores, tune thresholds, or access astronomical powers. The existing
23/24 qualified-control status and all failed execution identities remain.

Before execution, publish this protocol, fixed JSON plan, source code, tests,
and the independent code review to GitHub; verify exact public readbacks.
Reserve each trial directory exclusively. Execute each trial once. Preserve
all bytes, traces, actual child exits, natural pipe EOF and cleanup receipts.

Three fixed trials use unrelated deterministic records: two streams of
45,000 records each, around the size of the damaged association streams.
The original BQ writer and BR publisher are used without weakening checks.
Trials: BQ serial; BR serial; BR with an overlapping read-only execution.
The last trial is deliberately paced 100 ms per 1,000 records; the separate
witness takes two read-only file observations six seconds apart and writes
only its own receipt. No witness intentionally truncates or changes payloads.
No additional tool command will overlap the serial trials. Both workers use
Python audit-hook file-operation logs and a file event/metadata monitor.
A preliminary strace capability probe failed with PTRACE_TRACEME Operation
not permitted before any full-size trial. The replacement audit log is not
a syscall trace: write/fsync calls and external-process attribution are not
captured. Monitor failures and lost events remain visible limitations.

The prediction being tested is whether an execution/workspace interaction
can replace a later file with an earlier prefix and earlier permissions.
The mode-0600 retained BR pending file is a lead, not causal proof. Ordinary
buffer loss is a competing explanation, though the historical code performs
flush/fsync/close and its initial expected-size check passed.

Any content mismatch means the trial did not establish integrity. A complete
serial trial and a failed overlapping trial would support isolating the
writer from concurrent execution; it would not by itself identify the exact
platform mechanism or retrospectively repair BQ/BR. Passing all three trials
would mean the failure was not reproduced within this bounded investigation.
An independent review must compare final files, declared receipts, traces,
monitor observations and actual process exits. No automatic A04 retry is
authorized by this diagnostic stage.

Caps: 120 wall seconds, 90 CPU seconds, 512 MiB observed process-tree RSS and
384 MiB stored bytes per trial; 1 GiB cumulative retained diagnostic bytes.
Total at most three trials. No loop until success. The exact caps, parameters,
source and historical hashes are fixed in BS_FILE_STABILITY_PLAN.json.
