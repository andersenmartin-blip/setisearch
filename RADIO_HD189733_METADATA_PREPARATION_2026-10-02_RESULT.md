# HD189733 — prospective metadata component prepared

**PASSED_METADATA_COMPONENT_PREPARATION_ONLY; TELESCOPE_ACCESS_BLOCKED.** A
distinct pure metadata constructor and separately callable validator are now
integrated. The candidate's **42 tests pass**, and an independent isolated
42-test run and metadata reconstruction pass without actionable blockers.
All 42 metadata tests also pass inside the final fourteen-module **401-test
suite**, with zero failures, errors or skips. All 25 original inputs have fresh
immutable public byte/Git-blob readback, and fresh o capture and independent
audit pass with execution blocked. New component/output publication remains
pending. No executable source contract, detector certificate, trial, acquisition
allocation or spectral authority is issued.

This advances the concrete interface work identified in the
[source admission matrix](RADIO_NEW_SOURCE_ADMISSION_MATRIX_2026-10-02.md).
The [failed compact control b](RADIO_NATIVE_V2_COMPACT_CONTROL_2026-10-02B_RESULT.md)
remains `CLOSED_FAILED`, with zero completed cases and its one invocation spent.
No retry, resume, marker rearm or retrospective qualification follows from this
metadata preparation.

## Integrated component and input custody

| Integrated file | Bytes | File SHA256 |
|---|---:|---|
| [Pure constructor/validator](src/seti_repeater/prospective_source_metadata_radio.py) | 31,819 | `2852d23d30619e2406c36f46ffee2452fd64cd3834e31f18a7bb1f0ac8081360` |
| [Adapted repository tests](tests/test_prospective_source_metadata_radio.py) | 22,278 | `e30c61490af7df85db04a72e05aa00d658fdb0a5bbf61988ed6b7ce3ed220f73` |

The source is byte-identical to the reviewed candidate. Test adaptation changes
only the package import, repository/results input locations and static AST
source location; it retains the same 42 test methods. Candidate test receipts
retain their original candidate test pin and are not relabeled as integrated
full-suite evidence.

[The independently supplied raw pin map](results_radio_hd189733_metadata_preparation_20261002a/evidence_pins.json)
binds **25 files / 749,088 bytes**: the matrix's 19 original metadata/interface
inputs and six supplemental implementation files. Raw SHA256 and byte counts
match immutable local Git blobs at
`58e7a883bf8ccf7951e8365f658d7b6645f161e4`. The independent review also matches
all nine selected current source/acquisition implementation files to repository
bytes. [Input custody](results_radio_hd189733_metadata_preparation_20261002a/evidence_origin.json)
retains this original local Git verification. The subsequent
[fresh public input readback](results_radio_hd189733_metadata_preparation_20261002a/public-input-readback.json)
independently verifies all **25 inputs / 749,088 bytes** and their exact Git-blob
identities at immutable commit
`1468a19d2603bde2b491b5400a2d3cdf8954c69f`. It was a primary GitHub connector
lookup outside the pure constructor and failed control. Its 6,647-byte proof
has file SHA256
`cc2edaba14e41be9062ce3feccdbb9b8de47edac913ebdf6378dfd1d02a19b6c`.
No selected source text was executed by readback. Public input custody does not
qualify the intended HDF5/source runtime, active admission or scientific gates;
new component and output publication/readback remain separate and pending.

Ten historical JSON files absent from the local checkout were materialized at
their original tracked paths, byte-identical to those retained Git blobs.
[The materialization record](results_radio_hd189733_metadata_preparation_20261002a/historical-metadata-materialization.json)
records their exact paths, counts and hashes. No historical contract/result was
rewritten, no duplicate source-code evidence tree was added to results, and no
spectrum or holdout was accessed. Source text is authenticated as raw bytes;
the constructor never imports or executes that selected source text.

The selected implementation closure is the eight current
`source_radio.IMPLEMENTATION_PATHS` entries plus `acquisition_radio.py`. Four
old-contract gaps are explicit:

| Original preparation gap | Current selected binding |
|---|---|
| Guarded reader changed from its old pin | `source_radio.py`: `d189028cacf05482a8b9a74a9544d30a1c45cd60f95784be5f06b2ce093e677f` |
| Search implementation also changed from its old pin | `search_v0p6.py`: `6bac0d68d76d818d49d57e3b6a19b30b1e6c2ef25c9d06b9c25a1ab2321ac7e4` |
| Filter-contract pin was missing | `hdf5_filter_contract_radio.py`: `65533ad8ead2bd7283beee9645a18b3a652a3ede50425573b64aaca69120e6a6` |
| Durable acquisition pin was missing | `acquisition_radio.py`: `c98d65aa8d46ef8f4a1003dc55cfc542c7c63bde01272325dc1d1a7054fa8712` |

The original preparation, window binder, receiver-bank provenance APIs and live
source guards are preserved. Old identities are ancestry; they are not relabeled
as a new executable source freeze.

## Pure bytes interface and retained outputs

`build_prospective_source_contract(raw_files, expected_file_pins, *,
expected_source_inventory_sha256, ...)` authenticates exact raw evidence and
returns a dictionary of **three canonical UTF-8 byte documents**. It performs no
filesystem operation. Each input pin is exactly an integer byte count and raw
SHA256 supplied independently by the caller.

`validate_prospective_source_metadata(outputs, expected_output_pins, raw_files,
expected_file_pins, *, expected_source_inventory_sha256, ...)` authenticates
separate retained output pins and reconstructs source/window/clock closure
without invoking the builder. Both entry points share pure canonicalization and
semantic helpers; separate validation is **not a claim of independently
implemented algorithms**. Neither entry point calls source runtime/load/extract,
acquisition start/genesis, HTTP, filesystem, subprocess, RNG, scoring or LS APIs.

| Retained canonical output | Bytes | Raw output SHA256 |
|---|---:|---|
| [Prospective wrapper](results_radio_hd189733_metadata_preparation_20261002a/prospective_wrapper.json) | 10,243 | `4384ede2efeca7b61791db970bb00c161685db603fa5534dd3777eea1512ca69` |
| [Admission sidecar](results_radio_hd189733_metadata_preparation_20261002a/admission_matrix.json) | 19,481 | `5fb18c824b00e12f34a1ff86d04a62096f62ff0053ceb0f97b99b03c1ae185a8` |
| [Pending provenance rebinding](results_radio_hd189733_metadata_preparation_20261002a/provenance_rebinding.json) | 15,189 | `d3c384edc8ef276c309b62991121ecc2080abea73ab3ff82a82e3be8b778925b` |

[The output pin map](results_radio_hd189733_metadata_preparation_20261002a/output_pins.json)
and [sample validation](results_radio_hd189733_metadata_preparation_20261002a/sample-validation.json)
match fresh constructor bytes. The wrapper has a distinct top-level artifact
type; safe `radio-source-contract-v1` fields appear only nested inside it, with
all three live source gates pending. It is never issued as an active source
contract. The rebinding receipt names the original raw source/window/bank pins,
but its new executable source-contract SHA is null and executable rebinding
admission is false.

All three outputs retain `PROSPECTIVE_TELESCOPE_ACCESS_BLOCKED`, six explicit
false authority flags, zero workload counters and the stop date `2026-10-09`.
Actual HDF5 runtime, complete execution freeze, source-bound codec/case/law
certificate, complete 127/24 scientific certificate, joined hosted transport,
distinct trial protocol, cumulative quotas, public reservation store/revision,
fresh irreversible acquisition/trial allocation and executable rebinding remain
explicitly missing. Future authority arguments are refused rather than trusted,
including a passed Boolean certificate or purported local/GitHub ledger.
The historical 500-request / 512 MiB / 1,200-second session ceiling is retained
only as an inactive declaration; no cumulative number or allocation is invented.

## Reconstructed scope and exact clock

The component recomputes the original HD189733/HIP98505 cadence85030 source
inventory, ordered six ON/OFF scans, retained header/filter/URL/size/ETag joins,
three roles and **288 distinct scan/row/native-chunk identities**. Each role
retains its 65,536-channel extraction, normalization partition and negative-foff
frequency convention. These three roles are portions of one cadence, not
independent observations.

The exact clock has **96 integrations × start/midpoint/end**, retaining the
original `Fraction` interpretation of decoded binary-float header numbers.
Its 10,702 canonical bytes reproduce historical receiver-bank SHA256
`807e59e40311d623231a13f05bd3bdf4801e83bacd90aae5f9f3b28380f02c48`.
The bank stays recorded-topocentric linear ±4 Hz/s in 0.1 steps: 81 rate labels,
81 scored carriers over **226.840273 Hz**, and widths
1/3/5/9/17/33/65/129. Extraction width is not the scored frequency span.

Historical bank identities, factor hashes and source/window/clock/rate/width
provenance are authenticated metadata references. **Factor bytes are not
regenerated or numerically requalified.** The inactive 127-reference/24-evaluation
proposal retains its ordered identities, EMPTY/inclusive-rank/tie rules and ten
ON-signal, ten matched ON/OFF, two adjacent-OFF and two noise-null recipes.
No score, random value, outcome, physical recovery or scientific certificate is
computed.

## Tests, independent review and remaining fork

[The retained candidate test receipt](results_radio_hd189733_metadata_preparation_20261002a/candidate-test-result.json)
records **42 passes in 0.845 seconds**, zero failures/errors/skips.
[Independent review](results_radio_hd189733_metadata_preparation_20261002a/independent-candidate-review.json)
records **42 passes in 0.570 seconds** under actual isolated/no-site/no-bytecode
flags, authenticates all 25 raw inputs and independently reconstructs the
six-scan/288-identity/rational-clock baseline.

Review found that ordinary Python equality accepted an output clock integer0
rewritten as float0.0 after the output was re-pinned. Canonical-byte comparison
now checks all reconstructed output collections and numeric-bearing input
metadata. The original float and Boolean clock substitutions refuse, as do
header/bank numeric aliases. Meaningful negatives also cover old source/search
pins, missing implementation closure, last-OFF/ETag substitution, overlapping
roles, expanded scope, changed session limits, incomplete/spent proposal,
weakened rank/EMPTY/ties, fake certificate/runtime/ledger authority, coherently
rehashed output forgery, unknown fields, duplicate/nonfinite JSON and exact
bounded metadata inventories. No detector/codec/source workload was repeated.

Parser bounds are 512 KiB per raw file, 2 MiB total input and 256 KiB per output.
These bound metadata parsing; they do not widen engineering, acquisition or
scientific workload caps. [The review contract](results_radio_hd189733_metadata_preparation_20261002a/REVIEW_CONTRACT.md)
retains the exact interfaces and limitations.

[The first extended full-suite attempt](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-attempt-2-summary.json)
retains **398 tests, zero failures, one error and zero skips**, with a
223.321274-second wrapper interval; all source/test pins stayed unchanged.
[Its log](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-attempt-2-stderr.log)
records all 42 metadata tests passing and the existing tiny observer failing on
`JSON evidence changed during read`. The separate typed publication-drift repair
adds three regressions and preserves this failed attempt.

[Final attempt3](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-attempt-3-summary.json)
passes **401 tests, zero failures, errors or skips**, including all 42 metadata
tests. [Its log](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-attempt-3-stderr.log)
records 246.436 seconds of tests; the wrapper interval is 251.539299 seconds.
All **944 source/test pins** remain unchanged. The 244,195-byte passing summary
has SHA256 `52fbf0faa40e23ea199e99cca53c32b64b0ba242d8be573f5e94ab24565e9636`.

The harness process exited1 after testing, on `FileExistsError` while exclusively
creating an already-present final alias. The retained attempt3 summary and all
attempt logs/results remain retained. The prior 356-test alias is preserved as
[the first passing summary](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-first-passing-summary.json);
[explicit final selection](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-selection.json)
selects the passing attempt3 summary byte-for-byte as the
[current final alias](results_radio_native_v2_supervisor_receipt_20261002a/final-suite-summary.json).
Selection changed no source/test/wrapper and reran no tests. The post-test
publication error is retained separately from the passing test result.

[Fresh o capture](results_radio_native_v2_supervisor_receipt_20261002a/preparation-capture.json)
and [independent verification](results_radio_native_v2_supervisor_receipt_20261002a/preparation-verification.json)
complete with exit0 and no stderr. Verification retains
`PREPARATION_COHERENCE_VERIFIED_EXECUTION_BLOCKED`, with **36 inputs, 927 repository
code files and 1,366 runtime paths**. Capture, fresh independent launcher
preflight, auditor and parent checks actually execute under the exact ten-value
environment and Python `-I -S -B`. The snapshot includes the metadata component,
test, six output/pin inputs and twelve original JSON inputs. The 27,511-byte
verification has SHA256
`227472dbecff37b0c45cf6283edbfccc12ac76a163c128d873b53a72f8e8c2fa`.
No new activation, spend, protected control, source generation or scientific
authority arises. New component/output immutable publication/readback remains
pending. Passing preparation cannot qualify control b or admit the pilot.
The next fork remains the
separately frozen hosted transport join, distinct fresh native8 engineering
freeze/reservation and physical feasibility, separate 127/24 scientific execution
certificate, then source-specific protocol/runtime/acquisition/trial admission.

HD189733 stays selected; HD1461 HOLD; GJ724 reserve; spectra and holdouts unopened;
native8 unreserved; **127/24 NOT ACTIVATED**; LS paused; CHEOPS UNSENT. No new
source generation, protected control, reservation mutation, RNG draw, native or
scientific case, telescope request or external person-directed message occurred
for this metadata preparation. Stop **9 October 2026** without automatic
extension, restart, target switch or return to LS.
