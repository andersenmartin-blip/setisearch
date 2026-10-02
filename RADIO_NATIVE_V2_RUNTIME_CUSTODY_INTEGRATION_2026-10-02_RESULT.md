# Radio native v2 — runtime custody integrated into blocked preparation

**Result: PASSED_RUNTIME_CUSTODY_INTEGRATION_PREPARATION_ONLY.** The freezer,
activation receipt, seven worker-role checks, outer entry and final-report writer
now use the reviewed custody policy. **272 relevant tests pass in 135.290 seconds,
with zero errors, failures or skips.** The explicit real-host audit was enabled.
The fresh plan remains **BLOCKED_PREPARATION_REVIEW**. This package invokes no new
protected control and creates no real activation marker.

## What changed

The v2 manifest records exact local per-path bytes, SHA256, mode, link count,
owner/group, allocated bytes and modification/change timestamps. Stable
`O_NOFOLLOW` reads check ancestors, held descriptors and named identities. Git
hardlink groups are hashed once per held inode and closed against bounded,
independently derived alias roots; late mutations are rechecked before return.
Device/inode numbers remain transient observation data, not published portable
identities. The metadata is an exact local custody observation, not a cross-host
identity or a kernel-integrity claim.

Activation validates the full runtime topology before its first Git call. Both
the custody source and the installed Git path/bytes/hash have independently
reviewed bootstrap pins. Candidate manifests cannot select a different alias
policy or executable. The activation Git environment fixes no-lazy-fetch and
no-prompt flags after stripping inherited Git settings; conflicting-parent tests
verify that the flags cannot be removed. The Git phase closes before the receipt is returned; a
final material check then precedes the required
`activation_only_runtime_complete=True` receipt field. The receipt binds the
manifest SHA256 and exact absolute `control_scope`.

Subsequent worker checks read material runtime only: they neither reopen installed
Git nor enumerate its activation-only alias roots. Historical freezes can still
be inspected, but current admission requires both custody fields. The known spent
marker and activation commit are explicitly refused. The prospective `20261002b`
marker name is only an interface constant; no such file is created in this package.

The outer timing anchor now includes initial admission. A renewed material gate
precedes final-writer launch. The production writer independently checks its
bootstrap sources, all **26 copied material files** and **three derived files**,
with exact bounded file/directory inventories, before compiling the fixture or
writing its identity. Extra/missing files, empty directories, symlinks and hardlinks
fail. Path bytes/components are bounded before directory-prefix allocation.
Relocated copies are checked by sole-link stable reads and exact bytes/inventory;
the original runtime's timestamps are not applied to relocated copies. Mutation
after a completed observation remains an explicit filesystem limitation.

The tiny report-writer probe has its own CLI/schema and limits: **64 KiB input/report,
2 MiB complete scope and three seconds**. Synthetic observations cannot certify
production termination. Even an actually observed tiny fsync/exit remains an
engineering probe with `complete_resource_measurement_join_qualified=False`.

## Fresh snapshot and independent verification

The snapshot was created only after the passing suite, with source/test pins
unchanged throughout that suite and rechecked before capture.

| Evidence | Measured result |
|---|---|
| [Plan revision l](config/radio_native_v2_compact_eight_input_control_20261002l.plan.json) | 65,275 bytes; SHA256 `0652f306f60b3f0801cd1860ead2767cad3333628f076a7e16cfee06d987e9a6`; blocked and non-authorizing |
| [Fresh original runtime freeze](config/radio_native_v2_runtime_custody_integration_20261002b.runtime.json) | 1,005,044 bytes; SHA256 `6206444e4f06d3ae9c178c2a9e875a27c5f72140057b565eb122b121ed14d480` |
| Original freezer scope | 924 repository code files, 14 preparation/test inputs, 1,366 runtime paths |
| Runtime lifecycle | 202 activation-only paths; 1,164 sole-link material paths |
| Git topology | 151 hardlinked inventory paths, six groups, 157 closed aliases |
| Canonical custody-manifest SHA256 | `dfb4f2f9d81171342796f9ce0e580906864d27f87dac549c8395efb51ef1873b` |
| [Independent preparation audit](results_radio_native_v2_runtime_custody_integration_20261002a/preparation-verification-final.json) | Original code/runtime scope, full activation custody, 26 material files and three derived files verified; auditor implementation bound by freeze |
| Actual post-activation file check | Passes while process creation and alias enumeration are forbidden |
| Actual parent/platform check | Exact ten-value public environment, `-I -S -B`, bounded platform contract; no ambient credential/session inheritance |
| Runtime plus historical supplement | 1,605 union files; supplement retains its existing byte/sole-link checks, not v2 observation-metadata coverage |

The full tests cover same-byte sole-link replacement, reconstruction of an entire
Git hardlink group with identical bytes/topology, hidden/removed aliases, hash and
metadata drift, descriptor/stat races, unexpected material hardlinks, self-selected
source/executable/policy, receipt scope/hash/completion drift, spent identities,
deleted Git after activation, copied-source tampering and synthetic writer claims.
Separate reviews found and corrected the late-Git-link race, writer inventory
coverage and path-allocation bound before final verification.

Reproduction and retained evidence:

- [Ten-module suite runner](results_radio_native_v2_runtime_custody_integration_20261002a/run_adjacent_suite.py),
  [passing summary](results_radio_native_v2_runtime_custody_integration_20261002a/final-suite-summary.json)
  and [complete passing log](results_radio_native_v2_runtime_custody_integration_20261002a/final-suite-attempt-3-stderr.log).
- [Snapshot construction](results_radio_native_v2_runtime_custody_integration_20261002a/prepare_snapshot.py)
  and [read-only independent verification](results_radio_native_v2_runtime_custody_integration_20261002a/verify_preparation.py).
- Component histories: [custody/freezer](results_radio_native_v2_runtime_custody_integration_20261002a/own-suite-history.json),
  [activation/admission](results_radio_native_v2_runtime_custody_integration_20261002a/activation_admission_tests_final_summary.json)
  and [reviewed final writer](results_radio_native_v2_runtime_custody_integration_20261002a/finalizer-post-git-policy-47-tests-passed-summary.json).
- Retained failures: [initial audit fixture](results_radio_native_v2_runtime_custody_integration_20261002a/audit_tests_attempt_1.json),
  [draft fixture log](results_radio_native_v2_runtime_custody_integration_20261002a/fixture_tests_attempt_1.log),
  [first activation/admission attempt](results_radio_native_v2_runtime_custody_integration_20261002a/activation_admission_tests_attempt_1.json),
  [writer negative-test setup](results_radio_native_v2_runtime_custody_integration_20261002a/finalizer-first-40-tests-failed-summary.json)
  and [superseded first full suite](results_radio_native_v2_runtime_custody_integration_20261002a/final-suite-attempt-1-disposition.json).
  The first full suite had 17 failures/10 errors: missing test import context and
  code changed after import caused integrity refusals. It is not final-source
  validation. The subsequent 271-pass revision k/runtime a snapshot was
  [superseded before publication](results_radio_native_v2_runtime_custody_integration_20261002a/pre-git-policy-snapshot-disposition.json)
  by the final Git-policy fix and distinct revision l/runtime b snapshot. Its
  files and observed verification remain retained historical preparation.
  Some earlier complete consoles were unavailable; their summaries
  explicitly record that limitation rather than reconstructing logs.
- [Payload inventory](results_radio_native_v2_runtime_custody_integration_20261002a/payload-manifest.json)
  and [immutable science/main publication readback](results_radio_native_v2_runtime_custody_integration_20261002a/publication-readback.json).

## Execution remains blocked

The source-worker guard still calls `require_execution_ready()` without a receipt
and fails before source generation. Authenticated receipt delivery to that guard
and persistent one-invocation consumption/replay resistance are **not implemented**.
Binding a receipt to a scope and denying the known spent identity do not close
those gaps. The new plan records both gaps as false completion fields.

No fresh execution-qualified preread or marker is made. Public readback of this
preparation package cannot supply execution authority. Complete eight-input
resource/lifetime/transport joins and scientific/native gates remain unqualified;
the original five execution blockers remain in the plan. Kernel bytes, external
tool transport and broader runtime coverage remain unclaimed.

The [failed earlier control](RADIO_NATIVE_V2_ONE_CONTROL_2026-10-02_RESULT.md) remains
`CLOSED_FAILED_RUNTIME_CUSTODY_POLICY_MISMATCH`. Its marker and invocation are
permanently spent. This work does not rearm or retry that evaluation.

The [2 October midpoint review](RADIO_TWO_WEEK_REVIEW_2026-10-02.md) records that
the independent astronomical pilot has not started. HD189733 remains selected,
HD1461 HOLD and GJ724 reserve. Telescope spectra and original holdouts stay unopened;
127/24 stays NOT ACTIVATED; native8 remains unreserved; LS stays paused and CHEOPS
UNSENT. This package has zero protected control invocations, large source inputs,
native/scientific executions, reservations, RNG draws, telescope reads or
person-directed external messages.

**Next:** implement and negatively verify authenticated source-worker receipt
delivery and durable one-invocation spending as a separate bounded preparation
package. Preserve the hard refusal until those checks are complete. Any future
control needs fresh immutable execution evidence and its own distinct activation;
the current package authorizes none. Consolidate the period on **9 October**, even
if the astronomical pilot remains blocked; no automatic extension or return to LS.
