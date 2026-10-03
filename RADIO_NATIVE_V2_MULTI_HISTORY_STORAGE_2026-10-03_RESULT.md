# Multi-generation historical storage preparation — 3 October 2026

**BLOCKED_PREPARATION_ONLY.** A pure bounded join now represents two or more
closed historical scope/journal pairs and one distinct prospective journal.
It does not create a journal, marker, scope, reservation or control and cannot
turn a public copy into a missing original private journal.

## Verified component

[`radio_native_v2_multi_history_storage.py`](scripts/radio_native_v2_multi_history_storage.py)
requires unique sorted generation labels, exact canonical pins for every scope
and journal observation, and a separately authenticated prospective spend
observation. It detaches every input at the pin boundary, checks complete
directory ancestry and totals through the existing retained-storage validator,
and refuses canonical root overlap, device/inode aliases, control-scope overlap,
extra/missing pins, malformed truth flags and the unchanged 32,768-entry / 1,536
MiB aggregate ceilings. Every row is labelled by generation and component.

The output keeps `execution_authorized`, `whole_control_qualified`,
`lifetime_accounting_proved` and `missing_history_reconstruction_authorized`
false. It performs no filesystem I/O itself and deliberately refuses a single
historical generation: the old b-only plus prospective-c contract is not
silently relabelled as the new b+c boundary.

The selected adjacent suite passes **61 tests** in 0.770 seconds with zero
failures, errors or skips and exit 0: 20 new boundary tests plus 41 existing
historical storage/spending/observation checks. Python compilation and
`git diff --check` pass. The [test summary](results_radio_native_v2_multi_history_storage_20261003a/test-summary.json)
retains two earlier non-passing development invocations: one missing test import
and one assertion that patched the shared pin ceiling before the intended join
ceiling. Neither is counted as a pass.

## c continuity is not fabricated

The separate archival verifier binds the exact five public c closure files and
produces this [non-authorizing receipt](results_radio_native_v2_multi_history_storage_20261003a/archival-closure-receipt.json):
`CLOSED_FAILED`, one launcher attempt, 0/8 completed and permanently spent.
It cross-checks the activation commit, spend hash and filename, terminal counts,
empty cases, source preservation and every retry/science bit. Its eight new
tests reject mutations even when the mutated bytes receive a fresh local pin.

The original c scope and private journal were rooted below the earlier absolute
checkout `/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002`. They are not
present in this restored checkout. The repository retains byte-exact public
closure records and a terminal inventory, including the 496-byte public spend
copy and the 68-file/21-directory terminal scope description, but these have
different storage identities and are not substitutes for the original live
scope/journal observations. The [prospective protocol](config/radio_native_v2_multi_history_storage_20261003a.protocol.json)
pins those public closure inputs while setting both original-live-presence and
missing-history-reconstruction authority false.

Consequently no actual b+c+future-d join is claimed and no fresh plan/freeze,
preread, marker or control is authorized. b and c remain CLOSED_FAILED, 0/8 and
permanently spent. The component is a reusable fail-closed interface for a future
preparation only if the required original observations are available through an
explicitly qualified continuity contract; it does not create such a contract.

## Exact continuation and unchanged science boundary

Next work may qualify an immutable archival-closure contract that explicitly
distinguishes public evidence from live retained storage, then integrate the
multi-generation join into fixture, worker, supervisor, finalizer and launcher
under a wholly fresh identity. Every phase must preserve separate b and c
dispositions, charge retained material once, and keep the old preparation
contract unchanged. If exact continuity cannot be established, record that as
the terminal engineering blocker rather than reconstructing or retrying c.

No protected invocation, RNG draw, large input, native/scientific case or
telescope value was opened. HD189733 remains selected; HD1461 HOLD; GJ724
reserve; spectra/holdouts unopened; native8 unreserved; 127/24 inactive; LS
paused; CHEOPS UNSENT. No person-directed message was sent. Consolidation remains
**9 October 2026**, without extension, target change or closed-control replay.
