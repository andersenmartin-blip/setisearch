# Radio native v2 — bounded supervisor receipt repair

**PASSED_SUPERVISOR_RECEIPT_REPAIR_PREPARATION_ONLY.** The supervisor receipt repair is
integrated after immutable publication and readback of failed control b. The
repair preserves full activation evidence inside the execution guards and stores
small observational references in terminal receipts. The complete pending and
final receipt capacity is checked before subreaper activation, scope creation,
identity writes or child launch. The original **131,072-byte** allowance remains
unchanged.

The final fourteen-module suite passes **401 tests**, with zero failures, errors
or skips. All **944 source/test/wrapper pins** stayed unchanged during the
**251.539299-second wrapper interval**; unittest records **246.436 seconds**.
The actual bootstrap uses the exact ten-value environment and Python `-I -S -B`.
Fresh plan o/runtime capture and independent preparation audit now pass, while
the plan remains **BLOCKED_PREPARATION_REVIEW** with all five execution blockers.
Independent final selection review passes; immutable public checkpoint G
readback remains pending.
This is preparation evidence; protected-control, native, source and scientific
qualification remain blocked.

## Failed checkpoint remains immutable and spent

[Failed control b](RADIO_NATIVE_V2_COMPACT_CONTROL_2026-10-02B_RESULT.md) remains
**CLOSED_FAILED**, with **0/8 completed engineering cases** and its unique durable
claim spent. Its original 107 files / 70,168,047 bytes remain retained, including
the 26 MiB deterministic source and 36,880,100-byte request part materialized
before the serialization failure. The repair neither changes those observations
nor supplies the missing original terminal receipts.

[The immutable failed-result readback](results_radio_native_v2_supervisor_receipt_20261002a/failed-control-public-readback.json)
verifies commit
[`1468a19d2603bde2b491b5400a2d3cdf8954c69f`](https://github.com/andersenmartin-blip/setisearch/commit/1468a19d2603bde2b491b5400a2d3cdf8954c69f),
parent `dab7a90b5dfd98227c9e09e5fb485c0ba1f77efe` and tree
`a8c3b48b513259d32e3964090a687d93115ce3b5`. All **155 publication paths** are
verified through overlapping **55 content-identical readbacks** and **139
immutable tree blob SHA/size readbacks**. The two large originals are retained in
31 byte-exact ordered chunks. These readbacks establish immutable failure/data
retention, not a completed resource or scientific join.

No retry, resume, rearm, new real marker, protected control invocation, production
ledger mutation or additional full-size source generation is part of this repair.
Historical failed markers and their invocation claims remain spent.

## Full guards and compact observational attestation

`check_admitted_worker` and its preparation compatibility entrypoint retain their
full raw checked return objects. Dispatch and supervision still independently
call the pinned fixture's `require_execution_ready` with the complete checked
activation receipt, plan, freeze, public preread, execution scope and durable
spend witness. Fresh checked-object equality, exact worker argv and receipt scope,
actual isolated/no-site/no-bytecode flags, the complete three-variable child
environment and exact supervisor interpreter argv remain required.

Only the persisted receipt copies replace the giant `activation_evidence` tree.
They retain exact role, ordinal, argv, admission-bundle path and independently
retained byte digest, worker/receipt/storage layout, structural admission fields
and authority fields. The replacement records the canonical byte length and
SHA256 of each of the **six full evidence components**, plus the exact canonical
execution scope. It explicitly states that the full evidence is not persisted
and that the reference is **not execution authority**. Recovery and revalidation
still require the independently retained exact admission bundle and full guards.

The pure reference verifier refuses changed component pins, scope, bundle, argv
or structural fields. Existing active consumers retain their exact role/ordinal/
bundle/argv checks; finalizer admission continues using the raw checked return.
Preparation retains both legacy `admitted_preparation_check` and
`admitted_worker_check` aliases. Their duplicate compact copies are counted twice
in the capacity calculation.

## Complete capacity before workload

Independent source inventory accounts for all **73 original pending/final
receipt fields** in disjoint fixed and dynamic sets. The bound includes exact
serialized fixed metadata, JSON keys/colons/commas/newline, all final-only fields,
**64 retained wait4 rows at 512 canonical bytes each**, caller callback state,
root/supervisor identity, numeric widths, escaped argv/input pins and bounded
failure diagnostics. Every dynamic field has an explicit serialization cap that
is checked again before persistence. Unknown checked, structural or input-pin
fields and arbitrary nested bulk are refused before workload.

Oversized fixed metadata fails before `set_subreaper`, `mkdir`, identity writes
and `Popen`. Oversized failure text is retained as an exact byte-count/SHA256
diagnostic reference while disposition stays `CLOSED_FAILED`. No retained row
allowance is reduced to make a receipt fit. The original exact pending/final
131,072-byte checks and filesystem postchecks remain in place; the example fit
does not claim that every future command's actual metadata fits.

| Original bound | Unchanged value |
|---|---:|
| Each pending/final supervisor receipt | 131,072 bytes |
| Retained reaped-process rows | 64 |
| Individual process RSS | 512 MiB |
| Case / eight-case run storage | 192 MiB / 1,536 MiB |
| Preparation/caller/lossless role deadline | 600 seconds |
| Command deadline | 120 seconds |
| Whole control/verifier deadline | 4,800 seconds |
| Generic tiny probe deadline | At most 10 seconds |

Admission, capacity checking, observation and cleanup remain inside the original
monotonic deadline. No resource limit or execution authority is widened.

## Live identity publication fix

The first extended suite exposed a separate genuine publication race in the
existing tiny finalizer-observation test. A child creates its identity path
exclusively and writes JSON before closing it; the production fixture likewise
exposes its exclusive path during write/fsync. The observer can see the path
while the opened descriptor's length or metadata changes during the read.

`small_json` now raises the specific
`JSONEvidenceChangedDuringRead(ValueError)` for either read-length mismatch or
before/after held-descriptor dev/inode/size/mtime/ctime mismatch. Only the live
identity poll, while the independently launched child's reported identity is
still unverified, retries that subtype alongside the existing `JSONDecodeError`.
The original deadline, sampling caps, wait4 owner, cleanup grace and writer stay
unchanged. Static evidence reads continue propagating the exception; ordinary
validation errors, stable wrong PID or parsed-invalid identity, aliases,
symlinks and oversized files still close the scope. An identity that remains
malformed or missing never acquires a verified-identity claim.

[Three deterministic new regressions](results_radio_native_v2_supervisor_receipt_20261002a/identity-publication-candidate-test-result.json)
and eight existing targeted observer tests pass. Both instability branches are
injected once during actual tiny-child observation, followed by a valid live
identity and direct reap. Stable wrong/invalid identity and an ordinary
`ValueError` close after one read; both static instability exceptions propagate.
[Independent review](results_radio_native_v2_supervisor_receipt_20261002a/identity-publication-independent-review.json)
finds no concrete blocker in the narrow source diff. The final suite includes
all three tests and retains the race failure as a distinct earlier attempt.

## Regression and integration evidence

[The retained candidate result](results_radio_native_v2_supervisor_receipt_20261002a/candidate-test-result.json)
records **six new regressions and 32 original tests**, all passing. It lists the
three deferred structural tests and their exact rationale: candidate source
deliberately differed from the still-frozen original admission pin, and no pin
bypass was used. [The integrated passing attempt 1](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-attempt-1-summary.json)
includes those tests after reviewed pin refresh, with 356 tests and no skips.
All remain included in the final 401-test pass.

The metadata regression reads the archived admission JSON only: full raw checked
evidence is **1,080,997 canonical bytes**, or **1,080,926 bytes** after rebinding
the example scope to the temporary candidate directory. A fresh actual Python
`-I -S -B` child runs in the exact three-variable environment; both guard calls
receive the full raw evidence, and the sole workload is a tiny fixed `print()`.
Admission and the exact dispatcher-prefix boundary are explicitly labeled test
doubles. Another actual isolated supervisor observes an oversized failed-launch
diagnostic and persists bounded `CLOSED_FAILED` measurements/disposition.
These tests generate no protected source, claim, marker or control.

| Role, tiny metadata example | Conservative complete-envelope bytes |
|---|---:|
| prepare, including both aliases | 64,600 |
| caller | 60,275 |
| command | 60,443 |
| lossless-project | 60,315 |
| lossless-verify-retained | 60,347 |
| control | 60,290 |
| verifier | 60,294 |

[The independent candidate review](results_radio_native_v2_supervisor_receipt_20261002a/independent-candidate-review.json)
finds no concrete blocker in the compact consumer
bindings, closed field inventories, exact preserved guards or capacity formula.
The refreshed source chain has these exact file pins:

| Material source | Bytes | SHA256 |
|---|---:|---|
| `scripts/radio_native_v2_compact_eight_case_resource_fixture.py` | 121,236 | `e108af6dd7cd649d82eb27148401db8075d9db49e2a973509eae43d44978fba1` |
| `tests/test_radio_native_v2_compact_eight_case_resource_fixture.py` | 65,797 | `ac5b3a3a7ef30e74cfca850fdea4d4b70a5c0c97d30d0ab1a64cef8312701777` |
| `scripts/radio_native_v2_process_tree_supervisor.py` | 71,827 | `3b5265342535a58330861b5d5250ffd4ea7e6b9f07d3222593985c0c387cd68e` |
| `tests/test_radio_native_v2_process_tree_supervisor.py` | 46,346 | `d8b143c6a07fe6019c737d785d18c18d5ad4fff9f03591bcbe2fc5e8a2cd293d` |
| `scripts/radio_native_v2_resource_finalization.py` | 73,131 | `7e7a04e65cae65a309dd88ebc99c42a33cb40c8f8f4baada4f3915fa898ebc4c` |
| `scripts/radio_native_v2_compact_control_launch.py` | 33,354 | `9bd4bcd55677dea320c7251ec34ce0d941cfbfed5371780dadd1fc8111cd48e3` |

The fixture's reviewed exception/catch change is followed by mechanical
supervisor→finalizer→launcher bootstrap-pin refresh.
[Final integrated source review](results_radio_native_v2_supervisor_receipt_20261002a/final-independent-integrated-review.json)
finds no concrete source blocker and preserves all raw guards and bounds. That
review explicitly predates final test/selection verification and makes no final
suite-pass claim of its own.

## Retained attempts and explicit final selection

| Attempt | Actual test disposition | Retained distinction |
|---|---|---|
| [1](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-attempt-1-summary.json) | 356 passed; zero failures/errors/skips; 237.343 wrapper seconds | First thirteen-module integration pass |
| [2](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-attempt-2-summary.json) | 398 tests; zero failures, one error, zero skips; 223.321274 wrapper seconds | All 42 new metadata tests pass; existing observer-publication race remains a retained error |
| [3](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-attempt-3-summary.json) | 401 passed; zero failures/errors/skips; 251.539299 wrapper / 246.436 unittest seconds | All final source/test/wrapper pins unchanged; suite process later exits 1 during final-alias publication |

Attempt 3 writes and closes its passing attempt summary before the wrapper's
exclusive creation of the already-existing `final-suite-summary.json` raises
`FileExistsError`. This is a retained post-test harness error, separate from the
401 passing test outcomes. The original 356-test alias is preserved byte-for-byte
as `final-suite-first-passing-summary.json`; all attempts and their logs remain.

[Explicit final selection](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-selection.json)
records process exit 1, the exact failing operation, preserved prior alias,
unchanged current source pins and selection of the byte-exact attempt-3 summary
as [the final alias](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-summary.json).
The selected summary is 244,195 bytes with SHA256
`52fbf0faa40e23ea199e99cca53c32b64b0ba242d8be573f5e94ab24565e9636`.
No code or wrapper changed and no tests or protected control were rerun for this
selection. [Independent final selection review](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-selection-independent-review.json)
verifies all 944 current pins, both byte-exact aliases and the post-test harness
error, with no concrete blocker. The review is 9,927 bytes, SHA256
`a8a9660d5d1f2cf1b67a6fc31ae9cf3ab7dbefa64d0b1c91a3c699286e3c525f`.

## Fresh blocked preparation and remaining work

| Evidence | Current disposition |
|---|---|
| Final fourteen-module attempt 3 | 401 passed; zero failures, errors or skips; all 944 retained source/test/wrapper pins unchanged |
| [Fresh plan o](config/radio_native_v2_compact_eight_input_control_20261002o.plan.json) | 66,878 file bytes; `BLOCKED_PREPARATION_REVIEW`; raw SHA256 `2057b7bce0d6607a6ccabe94f61f94f3b375ac87999c08ae5d6b2974d336b1ef`; canonical SHA256 `2595da2c2cbe788e79bcd6f391d8c220d3c2d84b3d0362b7b4d534b66a855c34` |
| [Fresh runtime freeze](config/radio_native_v2_supervisor_receipt_20261002a.runtime.json) | 1,010,023 file bytes; raw SHA256 `cad66a392cfee1baf8ffd409ccdcae49c245575936d2f7e82e679b7094f42a98`; canonical SHA256 `4cc5d107c0a6c6eba557c8388fa6e3097e2db2850c1617315c52a0a059611314` |
| Original named freeze scope | 927 repository code files, 36 inputs, 1,366 runtime files |
| Runtime custody | 1,164 material / 202 activation-only paths; six closed hardlink groups and 157 alias-closure paths |
| Runtime plus supplement union | 1,606 files; exact inventory and bytes independently checked |
| Material/derived preparation | All 33 copied code files and three derived files match |
| Fresh isolated launcher preflight | `LOCAL_PREFLIGHT_RECOMPUTED` in a separate fresh exact-environment `-I -S -B` process |
| Independent preparation audit | `PREPARATION_COHERENCE_VERIFIED_EXECUTION_BLOCKED`; exit 0 with no stderr |
| Final selection review | Passing result, all 944 current pins, aliases and explicit postlude error independently verified |
| Immutable public checkpoint G readback | PENDING |
| Complete resource/runtime/kernel/hosted-transport and scientific gates | Unqualified; all original completion/authority fields remain false |

[Capture](results_radio_native_v2_supervisor_receipt_20261002a/preparation-capture.json)
and [verification](results_radio_native_v2_supervisor_receipt_20261002a/preparation-verification.json)
themselves execute in the exact ten-value activation environment under actual
Python `-I -S -B`, with pinned source-only NumPy loading. Actual environment
fingerprints match the fresh freeze. Original runtime/custody closure, copied
material custody, material-only rechecks with process/alias scans forbidden,
independent supplemental inventory and the separately executed actual-parent
checker all pass their preparation checks. The verification is 27,511 bytes,
file SHA256 `227472dbecff37b0c45cf6283edbfccc12ac76a163c128d873b53a72f8e8c2fa`.
All five execution blockers remain; complete execution/runtime/kernel and
activation admission are unqualified. Public final checkpoint G readback remains
separate. Repair tests do not reopen the spent b scope or create an
execution-qualified preread/marker.

[The HD189733 metadata component](RADIO_HD189733_METADATA_PREPARATION_2026-10-02_RESULT.md)
now has **42 passing tests**, including the final suite. It authenticates **25
raw inputs / 749,088 bytes** against retained byte/SHA256 and immutable Git blob
identities. [Fresh public input readback](results_radio_hd189733_metadata_preparation_20261002a/public-input-readback.json)
at F independently matches all 25 input contents and blob identities. Its 6,647
bytes have SHA256 `cc2edaba14e41be9062ce3feccdbb9b8de47edac913ebdf6378dfd1d02a19b6c`.
The readback occurs outside the constructor and protected control; selected
source text is not executed and no telescope dataset or holdout is read. This
establishes metadata custody; execution-runtime match and active source admission
remain unqualified. Source
readiness, runtime, cumulative quotas, scientific certificates, hosted transport,
native allocation and telescope/acquisition/trial gates remain false or missing.
The [new-source admission matrix](RADIO_NEW_SOURCE_ADMISSION_MATRIX_2026-10-02.md)
still requires those original joins. Spectra and holdouts remain unopened.

HD189733 selected; HD1461 HOLD; GJ724 reserve; spectra and holdouts unopened;
native8 unreserved; 127/24 NOT ACTIVATED; LS paused; CHEOPS UNSENT. No new
native/scientific cases, telescope reads, RNG draws or person-directed messages.
Consolidate on **9 October** without automatic extension or restart.
