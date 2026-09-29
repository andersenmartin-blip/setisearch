# Native physical engineering result — closed with execution and failure-reserve failures

**Disposition: CLOSED_WITH_EXECUTION_AND_FAILURE_RESERVE_FAILURE.** Four new
same-window Gaussian references completed. The broad ON case stopped in receiver
receipt verification; narrow ON, matched ON/OFF and fresh null were never entered.
All eight reserved identities remain spent. No retry, replacement or refund.

The separate four-reference threshold is **UNCALIBRATED_ENGINEERING_ONLY**. Its
minimum possible inclusive rank is 1/5; it cannot pass the unchanged 1/100 cut.
Neither this run nor its later code correction qualifies production recovery,
RFI/null gates, 127/24, telescope admission or scientific 40/80-second timing.

## Immutable admission and actual outcomes

- Executable freeze: `53cc228c8d46ed20ea628ab211259a2956d570ff`.
- Freeze SHA256: `8eda48ebfe55e6a83e9b06abab48bee3ca2787456d866a914bbdce68712e71ad`.
- Irreversible public eight-case reservation: `6d56ee4449855827bf4e559d4117f6361e38b6e2`.
- All 16 changed freeze files and the reservation were independently read back
  from Git. Runtime closure covered 844 project Python files and 1,132 runtime files.
- 114 targeted deterministic preflight tests passed. Earlier test-schema mistakes
  and missing sparse fixture files are retained in `preflight_initial_failures.log`;
  the final passing log is separate. These tests drew no Gaussian values.

| Ordinal | Fixed case | Actual result | Case seconds |
|---|---|---|---:|
| 0 | Noise reference 0 | Complete, EMPTY maximum | 7.514 |
| 1 | Noise reference 1 | Complete, EMPTY maximum | 8.325 |
| 2 | Noise reference 2 | Complete, EMPTY maximum | 7.980 |
| 3 | Noise reference 3 | Complete, EMPTY maximum | 7.890 |
| 4 | ON, width129, −2 Hz/s, power500 | Failed at receiver signature receipt | 224.702 |
| 5 | ON, width1 | Not entered; allocation stays spent | — |
| 6 | Matched ON/OFF, width129 | Not entered; allocation stays spent | — |
| 7 | Fresh noise null | Not entered; allocation stays spent | — |

The four reference maxima are retained as EMPTY, giving the prespecified floor
threshold **10**. Five complete renders produced **31,457,280 Gaussian values**
through **480 normal calls**; no partial extra render occurred. The worker's
conservative generic failure flag permits partial draws in principle, but this
failure occurred after the fifth complete renderer/score archive was saved.

The broad case's complete maximum is **282.151123046875**. Exhaustive retention
kept **9,792 ON members**, zero OFF members. All 9,792 matched/local-OFF and
single-adjacent-OFF rows were retained; none was vetoed by those two stages.
**These are not final physical survivors or a successful recovery.** Receiver
identity partition, alias decisions, clusters and the recovery gate did not finish.

## Failure and the post-closure correction

The native receiver computes SHA256 over sorted compact JSON **with a final LF**.
The whole-cadence physical helper checked sorted compact JSON **without LF**.
The frozen run raised `IncompletePhysical('Receiver signature receipt changed')`
in `receiver_signatures`; the original native receiver receipt itself was not
saved by that failing implementation. The full upstream retention and completed
OFF-stage evidence were saved in the 14,979,354-byte partial report, along with
stdout and the complete traceback. Static inspection and fixed-signature
regression tests reproduce the incompatible byte domains; this is not a rerun
or remeasurement of the failed native receiver result.

The subsequent correction verifies the ORIGINAL native hash and source/context/
factor bindings, then creates a distinct whole-cadence bridge. It preserves the
original receipt and its native-byte hash, and does not overwrite or relabel it.
Both native physical entry points use that bridge. The shared physical helper
also retains returned signatures/receipt before its own receipt check. This fix
passed **6 new fixed-signature regression tests plus 34 existing physical tests**
in 1.832 seconds. **No Gaussian draw, native cache, failed case or closed experiment
was repeated to test this correction. It remains unqualified by a fresh live run.**

## Resource accounting and retained evidence

The worker failed after **257.016337 seconds** overall. The failed case's durable
finish event records 224.702 seconds, below its fixed 240-second ceiling. Live Git
usage was **9 local invocations, zero remote calls**. No peak-RSS-at-failure field
was recorded, so this report does not assert a measured final peak RSS.

The complete original journal occupies **798,836 bytes**, preserving **54 versions
and 53 events**. All live bytes, including the partial physical report, total
**25,826,464 bytes**, below the 208-MiB total. However, unregistered top-level live
setup/summary/failure files occupy **15,031,024 bytes**, exceeding the distinct
**8,388,608-byte failure reserve**. The worker did not enforce that sub-reserve
before saving its failure evidence. This is a separate resource failure. The
unused case-artifact capacity is not retroactively transferred to erase it.

A separate stdlib-only audit checked the original revision/event chains, exact
case artifact inventories and hashes, four-reference bindings, complete maxima
and irreversible failed state. A further byte/receipt audit checked all 9,792
retained members and both completed OFF-stage inventories without running the
physical algorithm again. Audit PASS means retained byte/state consistency,
not experimental success or overall budget compliance.

The lossless evidence archive contains **107 files / 25,839,931 original bytes**,
including all journal versions, score arrays, row receipts, partial physical
report, failure/stdout, audit and correction-test log. It is 9,199,504 xz bytes,
transported as 12,266,008 ASCII base64 bytes in twelve ordered parts. Every decoded
file was byte-compared against its original. The xz SHA256 is
`cdea42ff8dab83a707835e77715b0e5f139d5959b3d9fa00da435fc925d89726`.
See `results_radio_native_chain_engineering_2026-09-29/archive_manifest.json` for
all file/chunk hashes and decoding order. The archive cannot reconstruct omitted
native arrays and cannot create a lease or restart a case.

## Exact continuation

Keep this eight-case namespace closed. Before any future fresh engineering
invocation, integrate the corrected native receipt bridge with bounded durable
physical-stage evidence, ensure interrupted/failed evidence is charged to an
explicit prospective allocation, and capture final failure RSS and stage timing.
Use the observed 9,792-member/14.98-MB partial report when sizing and batching
incremental remote publication; a 217-byte witness does not predict that load.
Do not merely increase the failed reserve, replay case4, retune the signal, or
reuse the three unentered but spent identities. A future complete native run
requires a separate fixed scope, fresh identities and public freeze/reservation.

Actual 127 same-law references remain necessary for the production-shaped test.
Scientific 127/24 remains NOT ACTIVATED. HD1461 pointing HOLD, M43/LS/CHEOPS holds,
all previous counters/failures and 9 October consolidation remain unchanged.
Telescope spectra and old holdouts remain unopened; no external messages sent.
