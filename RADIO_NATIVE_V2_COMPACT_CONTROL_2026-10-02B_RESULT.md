# Radio native v2 — compact engineering control b failed

**CLOSED_FAILED.** The single authorized engineering invocation exited with code
**1**. The retained launcher failure covers **45.156232460 seconds** from its
admission anchor. **Zero of eight cases completed.** The durable invocation claim
was spent before workload and remains spent after failure. No retry, resume or
rearm is permitted by this result.

Case00 materialized a **26 MiB deterministic source** and a **36,880,100-byte
request part** before preparation receipt serialization failed. This is actual
partial engineering workload, not a preparation-only checkpoint. No native or
scientific case ran; no telescope spectrum or holdout was opened. The earlier
**350 passing tests** establish preparation, not successful control qualification.

## Immutable admission and one invocation

The retained public readbacks bind this exact chain. Execution stayed at A while
B published evidence and the fixed launch configuration; B did not alter code,
plan, freeze, preread or marker.

| Stage | Commit | Retained evidence |
|---|---|---|
| C: ledger/launcher preparation | `dbfcde247517b5d457e8faead62be96be9f818a5` | [40-file preparation readback](results_radio_native_v2_ledger_launch_20261002a/preparation-public-readback.json) |
| P: separate engineering preread | `2ff327021154ae966e52fb142668aaf11e39cee4` | [Distinct preread](results_radio_native_v2_ledger_launch_20261002a/distinct-preread-result.md), immediate parent of A |
| A: marker-only activation b | `1bc31d49b2552de10c3fbabb7bc106618a44a241` | [Marker readback](results_radio_native_v2_ledger_launch_20261002a/activation-public-readback.json) |
| B: launch evidence/config | `dab7a90b5dfd98227c9e09e5fb485c0ba1f77efe` | [Unchanged execution-source/config readback](results_radio_native_v2_ledger_launch_20261002a/launch-public-readback.json) |

[The unique invocation start](results_radio_native_v2_ledger_launch_20261002a/unique-invocation-start.json)
allows at most one launcher invocation and binds configuration file SHA256
`97c8f0f66c9e5b8fd20f14ac6eb17e645c4bfc0dded488b40da32c054cea9ee4`.
[The retained public claim copy](results_radio_native_v2_ledger_launch_20261002a/invocation-ledger-claim-public-copy.json)
records `SPENT_BEFORE_WORKLOAD`, exact A and exact b scope. Its file SHA256 is
`f28120ed840a8052589890548a30a825ed1d320a8fcbef7b590d8e67b7358e50`.
Independent read-only forensic review verifies the durable one-record witness,
the scope binding and the unchanged live ledger. The directory and sole record
account for 4,592 logical and 8,192 allocated bytes at that observation; this is
accounting evidence, not a complete resource pass. The witness is authenticated
through the independently retained admission-bundle digest.

## Observed failure and measurement limits

| Observation | Retained result | Qualification limit |
|---|---|---|
| [Launcher failure](results_radio_native_v2_compact_control_20261002b/compact-control-launch-closed-failure.json) | `CLOSED_FAILED`; 45.156232460 s from admission anchor; child failure/unexpected stderr | Complete resource join false; observer's own future termination unqualified |
| [Direct fixture child](results_radio_native_v2_compact_control_20261002b/compact-control-launch-observation.json) | Exit 1; 22.640582218 s; kernel wait4 RSS 299,876,352 bytes; complete pipe output; direct child reaped | Entire direct-child lifetime observed; descendant scope and full runtime closure unqualified |
| [Control worker failure](results_radio_native_v2_compact_control_20261002b/closed-failure.json) | `Fixed child/control scope closed: preparation: 1`; completed cases `[]` | No successful case receipt |
| [Outer failure](results_radio_native_v2_compact_control_20261002b/outer-closed-failure.json) | `Fixed child/control scope closed: measurement-driver: 1` | No successful whole-control receipt |

The 45.156-second admission interval and 22.641-second direct-child interval have
different boundaries. The observed direct-child RSS is below the individual
512 MiB bound; it does not establish complete descendant RSS, storage, elapsed,
kernel closure or a joined eight-case pass. The first demonstrated failure is a
receipt-size failure, not demonstrated RSS or deadline exhaustion.

The required case00 preparation and whole-control
`subreaper-measurements.json` / `subreaper-receipt.json` are absent, as is
`compact-control-launch-disposition.json`. No caller result/summary exists.
Retained observation logs do not replace the missing descendant/ECHILD and
terminal receipt joins. The authoritative endpoint is the separately retained
closed-failure record.

## Concrete serialization cause

[The preparation stderr](results_radio_native_v2_compact_control_20261002b/cases/case00/preparation-stderr.log)
ends at the unchanged supervisor cap check:
`RuntimeError: Bounded supervisor measurements reservation exceeded`.
[Independent metadata-only forensic review](results_radio_native_v2_ledger_launch_20261002a/control-forensic-review.json)
matches the admission components to the retained plan, freeze, preread, activation
receipt and spend witness. The checked `activation_evidence` alone is
**1,080,997 canonical bytes**.

| Checked activation component | Canonical bytes |
|---|---:|
| Complete freeze | 1,005,932 |
| Plan | 66,877 |
| Public preread | 5,638 |
| Activation receipt | 1,331 |
| Execution-scope string | 108 |
| Invocation spending | 1,017 |

Both preparation admission reports repeat this full checked evidence in the
terminal measurement structure. The minimal double-check receipt is already
**2,162,099 bytes**, before remaining observation fields. The whole-control
supervisor's single-check minimum is **1,081,048 bytes**. Both exceed the fixed
**131,072-byte terminal measurements reservation**. Supervisor source lines
217/222/226 and 828/829 construct the oversized report; lines 840/841 refuse it.
The original cap was enforced rather than widened.

Generation had returned before the preparation terminal serialization failed.
The failure then propagated through preparation, control worker, whole-control
supervisor, measurement driver, fixture and launcher. The whole-control
supervisor independently has the same serialization defect. This accounts for
partial materialization and missing inner receipts without claiming a completed
case or complete process-tree closure.

The passing preparation suite did not test serialization of the actual
freeze-size admitted report. Real admission-dispatch tests refused before Popen;
tiny probe receipts omitted the actual full admission tree. Those tests remain
valid preparation checks but do not prove production receipt fit.

## Retained partial data and evidence

The original failed scope retains **107 files / 70,168,047 logical bytes**.
The forensic review did not rerun admission or dispatch, generate another source,
make another spend attempt, edit production/tests, or read raw generated source
or archive data. Its 127-entry content/metadata inventory stayed unchanged during
review, SHA256
`3fa2a122de3c61672edbb7384d95f4b20d88031351350c10f1412a67e44008dc`.

The separate [retained-source verification](results_radio_native_v2_ledger_launch_20261002a/retained-source-verification.json)
verifies the existing case00 source against its exact deterministic counter
domain and prepared pin, with no additional source generation. It establishes
26 MiB of byte identity, not native case binding or a completed engineering case.
The prepared manifest declares 28 archive files / 36,875,057 bytes; this is a
manifest claim, distinct from the larger retained request part and from a final
joined archive/transport qualification.

| Existing large original | Bytes | SHA256 | Lossless representation |
|---|---:|---|---|
| `cases/case00/deterministic-source.bin` | 27,262,976 | `dcf48f32d94de70df4dae8dca7fc3f25e8388f0d60b87f8691931c87ccb5339a` | 13 ordered chunks |
| `cases/case00/store/items/request-000001/part` | 36,880,100 | `49541a6a84d1a286276af24c12742a4d54fd2e898f82caf086e3a658d58b4d3a` | 18 ordered chunks |

[The byte-exact chunk manifest](results_radio_native_v2_compact_control_20261002b_public/chunk-manifest.json)
maps both unchanged originals to **31 chunks / 64,143,076 bytes**, with maximum
chunk size 2 MiB, offsets, SHA256 and Git-blob identities. Local ordered
reassembly matches the original hashes. The direct whole-source blob transport
failed and does not claim remote creation. The separate
[upload journal](results_radio_native_v2_ledger_launch_20261002a/chunk-upload-journal.json)
records matching content-addressed chunk uploads; uploading those blobs alone is
not a final immutable result-commit/tree readback. Byte retention neither retries
the control nor changes its `CLOSED_FAILED` disposition.

The principal retained metadata pins are:

| Evidence file | Bytes | File SHA256 |
|---|---:|---|
| [Launcher closed failure](results_radio_native_v2_compact_control_20261002b/compact-control-launch-closed-failure.json) | 954 | `0ce7098e4743a41d1ebda59d4da642d50dbf82bb222c1a1fae09956152f04e15` |
| [Direct-child observation](results_radio_native_v2_compact_control_20261002b/compact-control-launch-observation.json) | 2,132 | `613805830605afcd774ea8c979de1596760ae4aed8e0a2b666d6e8ca1d326450` |
| [Forensic review](results_radio_native_v2_ledger_launch_20261002a/control-forensic-review.json) | 16,288 | `38a2296e3a7c12df46784042568957705fe54df6b1744fc33c1da6922c31b078` |
| [Source identity proof](results_radio_native_v2_ledger_launch_20261002a/retained-source-verification.json) | 807 | `1ddebc6df3c5664b1100fe1a53d14775e4b91f3b4ba49fac744b469c5749f764` |
| [Lossless chunk manifest](results_radio_native_v2_compact_control_20261002b_public/chunk-manifest.json) | 9,393 | `8f88e15caaffbb8f8ec55d37e13264e716ca09ec73a3760bfb036a00a2138e37` |

## Next bounded fork and scientific status

Control b is closed and spent. Preserve the original scope and ledger. A compact
attestation repair candidate exists only under `/tmp`; it is **not integrated,
frozen, published or admitted** in this result. The concrete code preparation is
to keep full evidence for authority validation while serializing bounded verified
digest/path/role/scope references, replace duplicated full evidence while
preserving the existing verifier aliases, and preflight the maximum terminal
receipt size before workload dispatch. Test the actual
freeze-size metadata and oversize refusal with tiny children under the unchanged
131,072-byte cap. Any future engineering invocation needs a distinct reviewed
freeze, immutable publication/preread and new marker transition; this result
provides no retry or activation authority.

[The new-source admission matrix](RADIO_NEW_SOURCE_ADMISSION_MATRIX_2026-10-02.md)
advances the independent pilot through pinned metadata without touching spectra.
It specifies the HD189733 six-scan header windows, fixed 226.840273 Hz / linear
±4 Hz/s scope, missing source/acquisition/runtime contracts, provenance rebinding
and scientific/transport joins. Metadata-only contract preparation can proceed
while this engineering refusal remains closed. An eventual compact8 pass would
still require the actual hosted transport join, separate native8 engineering
freeze/reservation and the separate 127/24 scientific certificate; it would not
admit telescope data by itself.

All retained failure counters declare zero native executions/reservations,
scientific cases, RNG draws, telescope reads, network fetches, SDK/connector calls
and real public GitHub mutations by the control. These are retained counters,
not a new network-trace audit; hidden HTTP bytes remain unknown. Complete
runtime/resource, kernel closure, native binding, hosted transport, scientific
execution and the terminal observer's own future lifetime remain unqualified.

HD189733 stays selected; HD1461 HOLD; GJ724 reserve; spectra and holdouts unopened;
native8 unreserved; **127/24 NOT ACTIVATED**; LS paused; CHEOPS UNSENT. No external
person-directed messages were sent. Consolidate and stop on **9 October 2026**
without automatic extension, restart or enlargement of the original limits.
