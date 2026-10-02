# Radio native v2 — authenticated source receipt and durable spending prepared

**Result: PASSED_ADMISSION_SPENDING_PREPARATION_ONLY.** The final twelve-module
suite passes **310 tests in 185.517 seconds**, with zero failures, errors or skips.
All tested source/test pins remained unchanged during that run. An independent
read-only review matched ten bootstrap pin comparisons; the fresh blocked
snapshot also passes the separate preparation audit.

This package creates no real activation marker and invokes no protected control.
The astronomical pilot has not started. The failed earlier marker and invocation
remain permanently spent.

## What changed and what was tested

The generated source worker previously called its execution gate with no receipt.
It now requires actual argv/environment, authenticates the exact bundle against
its independently retained argv digest, and delivers the bundle's receipt, plan,
freeze, preread, exact execution scope and spend witness before any source or
identity write. A receipt dictionary and self-asserted public-readback fields do
not establish public authenticity.

The outer runner now claims the prospective marker durably before its first scope
creation. A fixed original-repository ledger path is part of the current plan;
there is no CLI ledger override or incoming-witness bypass. Marker-level O_EXCL
serialization, file/directory fsync and stable readback precede witness return.
The claim key deliberately excludes scope and activation commit, so neither a
new scope nor a changed commit can rearm the same marker. Partial records and
failed writes, fsyncs or later gates remain spent. Every worker role, supervisor
and final writer rechecks the same bundle-bound witness and exact scope without
Git. The final writer reads the separately retained invocation-spending.json.

The **26 spending tests** cover simultaneous thread/process attempts, scope and
commit drift, missing/corrupt/partial records, symlinks, FIFOs, hardlinks,
same-byte inode replacement, receipt mutation and retained write/fsync failures.
The **12 source/integration tests** cover exact local delivery at ordinals 0 and
7, digest/path/receipt/witness substitution, actual argv/isolation and
consume-before-scope failure persistence. Positive source tests execute only the
production guard prefix plus tiny stdout; no generator is present. The full
26 MiB recipe remains a negative test with its witness removed.

The first complete suite retained one test-setup error: a malicious-bootstrap
negative fixture asked the valid-bundle builder to accept a changed receipt with
an old spend witness. The intended spend refusal prevented construction. The
fixture now constructs deliberately invalid canonical evidence directly, so its
independent bootstrap rejection is tested. Production code was unchanged by that
correction. [The failed log](results_radio_native_v2_admission_spending_20261002a/final-suite-attempt-1-stderr.log),
[summary](results_radio_native_v2_admission_spending_20261002a/final-suite-attempt-1-summary.json)
and [disposition](results_radio_native_v2_admission_spending_20261002a/final-suite-attempt-1-disposition.json)
remain retained.

## Fresh blocked snapshot

| Evidence | Result |
|---|---|
| [Plan revision m](config/radio_native_v2_compact_eight_input_control_20261002m.plan.json) | 66,149 bytes; file SHA256 `08b3cd38ead2b763e7e1944982c2a6a7c8fbb34f29b278861410320ec77870f8` |
| [New original-runtime freeze](config/radio_native_v2_admission_spending_20261002a.runtime.json) | 1,005,487 bytes; file SHA256 `bb934601586235d62eacb0f46b9e8200c085424e1bf2a9347902d1ae4d01b664` |
| Original freezer scope | 925 repository code files, 16 preparation/test inputs, 1,366 runtime paths |
| Lifecycle/custody | 202 activation-only paths, 1,164 material paths, six closed Git hardlink groups |
| Materialized preparation | 29 copied material files and three derived files verified |
| Independent parent/platform check | Exact ten-value public environment and actual `-I -S -B` isolated check pass |
| Post-activation runtime check | Passes while process launches and activation alias enumeration are forbidden |

Reproduction and evidence: [suite runner](results_radio_native_v2_admission_spending_20261002a/run_adjacent_suite.py),
[final passing summary](results_radio_native_v2_admission_spending_20261002a/final-suite-summary.json),
[complete passing log](results_radio_native_v2_admission_spending_20261002a/final-suite-attempt-2-stderr.log),
[snapshot builder](results_radio_native_v2_admission_spending_20261002a/prepare_snapshot.py),
[read-only verifier](results_radio_native_v2_admission_spending_20261002a/verify_preparation.py),
[actual audit receipt](results_radio_native_v2_admission_spending_20261002a/preparation-verification-final.json)
and [independent review](results_radio_native_v2_admission_spending_20261002a/independent-review.json).

## Admission remains blocked

The plan stays **BLOCKED_PREPARATION_REVIEW**. Its new component-prepared fields
are true; execution-complete/enforced qualification fields remain false pending
actual qualified admission. The production ledger is absent and no fresh
execution-qualified preread or marker is supplied. Publication does not activate
the preparation.

Spending trusts a stable private local ledger and the trusted outer bundle/argv
chain. It is not a standalone signature or protection against same-owner or
privileged deletion, rollback, copying or post-check mutation. There is no
removal/rearm API. The persistent record is bounded to 16 KiB and lies outside
the disposable scope; its allocated storage is not yet joined to the original
whole-scope resource account. Complete resource/lifetime/transport qualification
and native/scientific gates remain open. [The exact boundary](results_radio_native_v2_admission_spending_20261002a/BOUNDARIES.md)
retains these limitations.

**Next:** join the persistent ledger's allocation into the original resource
account with bounded refusal tests, then assess fresh immutable execution
evidence and a distinct activation. Preserve the hard refusal and the spent
historical evaluation; do not widen budgets or treat a component pass as a
scientific gate.

HD189733 remains selected; HD1461 HOLD; GJ724 reserve. Telescope spectra and
historical holdouts remain unopened; 127/24 NOT ACTIVATED, native8 unreserved,
LS paused, CHEOPS UNSENT. This package has zero protected control invocations,
new real markers, large input generations, native/scientific cases, reservations,
RNG draws, telescope reads or person-directed external messages. The period
closes on **9 October**, without automatic extension or return to LS.
