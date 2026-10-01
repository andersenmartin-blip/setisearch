# Radio native-v2: preparation audit and bounded process evidence

## Disposition

**PREPARATION IMPROVED; LARGE EXECUTION REMAINS BLOCKED.** The current eight-input
control is still `BLOCKED_PREPARATION_REVIEW`. Its run, control-worker, command-worker,
exec-child and verifier-worker entry points remain closed before side effects.
No maximum input, native reservation, RNG draw, scientific case or telescope
spectrum was opened in this continuation. The earlier real 26-MiB publication
component remains unchanged.

This batch fixes concrete observer defects, adds an independently implemented
read-only local runtime audit, and develops a dedicated Linux subreaper component
with a tiny-probe-only CLI. **89 relevant Python tests pass.** These are component
and preparation results, not eight-case resource or scientific admission.

## Corrected observer and fresh identity checks

The prior observer could accept a sibling's procfs PID because it trusted the
reported namespace PID. It could also wait indefinitely on inherited output
pipes after reaping its direct child, retain unbounded samples, and infer complete
descendant reaping from exit code zero. The revised observer:

- Independently maps the launched child using kernel PPid, NSpid and start ticks;
  its subsequent identity report must match exactly. Missing or substituted
  identity closes the observation.
- Keeps the root unreaped while pipes remain, retains its PID/PGID identity until
  bounded cancellation, and never signals a numeric group after root reaping.
- Uses `os.kill` and a sole `wait4` owner. `Popen.kill` can poll/reap implicitly
  and had lost the independent resource receipt in one regression invocation.
- Caps output prefixes and retained samples at 2,048; total sample count and
  kernel lifetime peak remain recorded. A deadline closes inherited pipes.
- Separates complete direct-child observation from descendant coverage, which
  remains explicitly `NOT_INDEPENDENTLY_VERIFIED` for this observer.

A new read-only source verifier compares each retained payload window with the
fixed ordinal's SHA256-counter domain, keeping at most 64 KiB of each actual and
expected window. Preparation and terminal identities then bind the independently
checked source digest, outer ordinal, source case ID, archive prefix and domain.
Boolean/numeric substitutions and relabeling are refused. The derived recipe
now declares its source domain, and the caller summary retains its terminal.
Only eight 65-byte source ranges were used by these new domain tests; full-size
verification and changed derived-template resources remain unmeasured.

## Independent local file audit

[The read-only auditor](scripts/radio_native_v2_compact_preparation_audit.py)
applies the original freezer's structural validator and independently recomputes
its actual named repository/runtime scope. Internally consistent subsets,
changed versions/executables, omitted dependencies, stale supplement files,
unauthorized flags, path aliases and altered environments are refused. It also
pins and rechecks its own already imported repository dependencies.

The actual replay verifies:

| Preparation quantity | Verified |
| --- | ---: |
| Repository code files | 919 |
| Frozen input files | 5 |
| Original Python/NumPy/Git/Node/ELF runtime files | 1,366 |
| Supplemental cache/OpenSSL files | 240 |
| Union runtime files | 1,606 |
| Actual inventory, materialization and independent audit | 14.560834 s |

All 14 prospective code files and three derived templates were copied into a
fresh temporary preparation directory and independently checked before its
removal. No copied recipe was executed. The parent's original environment
allowlist and the exact child environment/Python flags match.

The successful audit verifies the **original named local file scope and its
supplement**, not a complete future execution runtime. Complete parent environment,
actual child argv/admission, immutable execution preread, imported-code policy,
process lifetime, final storage/time and host joins remain open. Kernel, network
transport, Git configuration/interpreter and arbitrary external-module closure
are not established by the historical freezer's scope. All five original blocker
categories therefore remain explicitly open in the audit.

The new [blocked plan revision](config/radio_native_v2_compact_eight_input_control_20261001b.plan.json)
is 62,241 bytes, SHA256
`c39d96c0855134e448be9cb589514991ee6be7f0971ebe220a4e44b882fa781c`.
The [non-authorizing local freeze](config/radio_native_v2_compact_preparation_review_20261001a.runtime.json)
is 508,467 bytes, SHA256
`3eeba073a03a66570be69145428742f64de9a77569e666c57db6fd1935dd98b6`.
The old plan bytes and original eight proposed identities remain preserved;
their scope has never been executed. This revision grants no retry, reservation
or source-generation authority.

[Actual audit](results_radio_native_v2_compact_preparation_audit_20261001a/independent-preparation-audit.json),
[verification summary](results_radio_native_v2_compact_preparation_audit_20261001a/verification-summary.json),
and [reproduction script](results_radio_native_v2_compact_preparation_audit_20261001a/verify_preparation.py)
retain the complete comparisons and limitations.

## Dedicated subreaper component

[The new supervisor](scripts/radio_native_v2_process_tree_supervisor.py) runs in
a fresh dedicated process, verifies Linux subreaper activation, exclusively
owns `wait4(-1)`, records root/adopted-child resource receipts and requires root
status plus terminal `ECHILD` before component success. Identity-safe cancellation
uses pidfds. Output limits apply separately to stdout and stderr. Child counts,
retained receipts, storage and deadlines are bounded; timeout and incomplete
cleanup remain `CLOSED_FAILED`.

The default CLI accepts only six fixed tiny probes. It exposes no arbitrary
command or existing large/source worker. Generic reusable-function argv admission
remains a future integrating caller's responsibility. Namespace/ptrace escape,
complete descendant wait-chain proof and pipeline integration remain unqualified.

Two actual tiny component tests were independently observed from supervisor
launch through final receipt fsync and kernel termination:

| Tiny probe | Root/adopted wait4 receipts | Independently bounded maximum individual RSS | Supervisor lifetime |
| --- | ---: | ---: | ---: |
| Orphan | 2 | 15,335,424 bytes | 0.145 s |
| Double fork | 2 | 15,466,496 bytes | 0.151 s |

These measurements include each dedicated supervisor and the kernel maximum
from its reaped descendants; they are not a concurrent RSS sum. The outer test
driver's termination and the original case/run storage/time ledger are not joined.
No full-size harness qualification follows from these tiny tests.

[Orphan evidence](results_radio_native_v2_compact_preparation_audit_20261001a/independent-orphan/joined-small-test.json)
and [double-fork evidence](results_radio_native_v2_compact_preparation_audit_20261001a/independent-double-fork/joined-small-test.json)
pin the raw supervisor and outer observations.

## Validation and exact continuation

| Test group | Passing tests |
| --- | ---: |
| Small eight-input preparation/observer/domain tests | 15 |
| Independent preparation-audit negatives | 23 |
| Adjacent compact retained verifier | 15 |
| Original runner-freezer contract | 26 |
| Dedicated tiny subreaper probes | 10 |
| Total | 89 |

The initial observer failures, implicit-reap failure, and an adjacent invocation
missing the tests import path are retained with the corrected logs. The first
failure file contains the exact final output chunk and labels its missing progress
chunk; it is not represented as a complete raw invocation transcript.
No JavaScript implementation in the established transport was changed; new
derived preparation/caller templates pass syntax and small semantic checks.

**Next:** integrate the dedicated supervisor with the worker admission and final
disposition path. Every source-generating worker must independently verify exact
public preread, full materialized source/runtime/argv/environment bindings before
generation. Freeze the complete outer observer/storage/time allocations and
authoritative terminal disposition, then obtain immutable public execution-preread
evidence before one fresh eight-input resource control. The new domain/terminal
checks and full-size lossless helper must be measured inside that admitted scope.
The supervisor's generic function is not that admission integration.

Native physical/recovery/RFI/null controls, separate 127/24 validation and the
telescope acquisition/trial protocol still follow their separate gates. Native
cases are unreserved; 127/24 is NOT ACTIVATED. HD189733 remains selected, HD1461
HOLD, GJ724 reserve, spectra/holdouts unopened, LS paused and CHEOPS UNSENT.
No telescope-analysis start date is established. No external messages. Review
2 October; consolidate 9 October without extension.
