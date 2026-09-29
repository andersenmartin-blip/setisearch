# Parent physical-evidence integration — closed journal-capacity failure

The parent allocation now registers and charges physical checkpoint files directly,
with protected small closure files and strict inventory seals. **117 targeted
tests pass.** However, the one fixed large byte-only integration is **CLOSED FAILED**:
retaining a complete journal snapshot after each artifact exhausts the ordinary
portion of its 8-MiB journal allocation after **19 of 22** intended checkpoints.
The reserved outer failure footer and parent FAILED event succeed. No case is
rerun, no capacity is enlarged and no historical outcome is relabelled.

## Fixed operation and actual outcome

The [scope](RADIO_PHYSICAL_CASE_2026-09-29_SCOPE.md) binds the already public
14,979,354-byte failed report and seven case4 artifacts to one new engineering
**storage** identity. The source identity inside those bytes is provenance, not a
new reservation of the old native case. All expected view hashes, manifest,
allocation and code/test pins were retained before consumption.

| Measurement | Actual retained value |
|---|---:|
| Committed physical checkpoints | 19 / 22 intended |
| Registered case files | 190 |
| Case artifact bytes | 16,886,543 |
| Complete original journal versions | 193 |
| Original journal revision bytes | 7,952,097 |
| Journal directory bytes, including HEAD | 7,952,162 |
| Case plus journal bytes | 24,838,705 |
| Outer failure footer | 880 bytes |
| Physical parts beyond committed checkpoint | 4 files / 194,476 bytes |
| Peak process RSS at caught failure | 234,975,232 bytes |
| Elapsed time at caught failure, before final closure | 22.075965 s |

The 24-MiB case cap and total 32-MiB case/journal allocation remain intact.
The failure occurs when the next ordinary journal revision would consume the
512-KiB journal closure reserve. That reserve is inside the unchanged 8-MiB
journal cap. All accepted journal snapshots and the two closing events count.
The current representation cannot finish the declared 22-view workload.

The interrupted physical writer has no terminal physical footer and cannot
resume. Its four extra parts are retained and registered in the parent ledger,
but are explicitly **uncommitted to a physical checkpoint**. The parent closes
FAILED with a bounded reference to the last committed physical checkpoint;
there is no large unregistered post-failure physical dump. It is neither a
complete physical result nor a statistical EMPTY result.

## Implemented boundaries and tests

The optional engineering-only `artifact_groups` policy binds a physical
reservation hash, a plain filename prefix, at most 1,024 members, an exact seal,
and explicit closure byte reservations. All physical parts and checkpoints are
ordinary immutable journal artifacts; no second full data copy is made. The
physical writer receives only the parent quota minus 262,144 seal bytes and
65,536 outer-outcome bytes. Its own physical footer reserve stays inside that
remainder. The policy does not admit dynamic scientific manifests or existing
remote adapters.

The parent verifies every file against its registration, and the group seal
enumerates the complete dynamic inventory. No member can append after sealing.
Failed group status prevents successful completion. A five-second failure-only
window can write already-reserved small closure files after a timeout; entering
it irreversibly closes normal work. Lost acknowledgements or torn writes leave
an uncertain non-resumable lease, with all partial bytes retained.

The journal checks **cumulative** bytes of all original revisions before both
artifact writes and publication, including the transient HEAD file. Each new
journal snapshot is bounded at 128 KiB, with 512 KiB held for closing revisions.
The large failure demonstrates that this guard works and that full snapshots
are still the wrong live representation for this workload.

The final 117 tests comprise **22 new parent/group tests, 32 existing journal
tests, 34 physical fixtures, 23 physical-storage tests and six receipt-bridge
tests**. Both actual test logs are retained: the initial 115-test run and the
117-test run after adding the cumulative-history boundary tests. Both pass.
Tests exercise exact byte accounting, success/failure seals, altered bindings,
extra/symlinked files, protected reserves, timeout closure, exhausted finalization,
lost acknowledgement and torn writes, while preserving legacy fixed manifests.

## Separate read-only audit and diagnosis

The [post-closure audit scope](RADIO_PHYSICAL_CASE_2026-09-29_READONLY_AUDIT.md)
pins every retained source file before auditing it. Consumption, journal writes,
physical writers, RNG and native calculation entry points are blocked.
All **19 committed views** match their original independent hashes/lengths.
All **193 original journal versions** restore byte for byte. Every original file
remains unchanged, including the four uncommitted parts and both failure records.

The already-existing read-only history codec represents those **7,952,097**
canonical journal bytes in **101,896 bytes**. Its archive SHA256 is
`85fe94f4b5a70fedcabcefbe4900d5a8dff99a16adbb833120c1863bced6c171`.
This is exact event/history representation, not a compression discount applied
retroactively to the failed store. No old journal revision is deleted. It is not
a qualified writable incremental journal and creates no execution authority.
The read-only audit takes **3.176652 s** with **146,685,952 RSS bytes**.

There are **zero new random values, native scores or physical decisions** in
either large byte-only stage. Small unit fixtures remain engineering checks.
The earlier eight-case native failure, all its spent identities and its separate
failure-reserve excess remain unchanged.

## Complete evidence and exact continuation

[`results_radio_physical_case_2026-09-29/`](results_radio_physical_case_2026-09-29/)
contains the fixed inputs, failure result, both test logs, stdout, read-only audit,
compact history, full lossless archive and publication/readback accounting.
`archive_manifest.json` inventories every original by exact length/hash. Verify
or restore it without executing either fixture:

```sh
python scripts/radio_physical_evidence_archive.py --archive results_radio_physical_case_2026-09-29
```

**Next:** implement and prospectively qualify a durable incremental parent
journal for these dynamic artifacts, preserving all original revision identities,
all pointer versions, strict cumulative bytes and crash/lost-response boundaries.
Then use a separate fixed storage namespace to qualify the complete 22-view
handoff under the existing size limits. Never resume or retry `integration01`.
The existing compact read-only archive must not be mistaken for that live writer.
Measured batched public delivery of this package is administrative transport;
it does not qualify the per-case remote scientific adapter or 40/80-second timing.

Full native receiver/alias evidence, recovery/RFI/null gates and scientific
calibration remain unqualified. **127/24 stays NOT ACTIVATED.** Telescope spectra,
old holdouts, all source selections/holds/counters, LS pause and CHEOPS UNSENT
remain unchanged. No messages or delegation. Consolidate 9 October without
extending the plan.
