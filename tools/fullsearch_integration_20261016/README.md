# Complete-search payload integration — 16 October 2026

`SETI_FULLSEARCH_PAYLOAD_ENGINEERING_20261016_V1` passed all three guarded phases: actual complete detector execution and new payload writing, independent complete-search QA, and the unchanged legacy full-case consumer. This validates the pipeline implementation on one constructed engineering fixture. The scientific detector and its search rules were unchanged. These are not sky results or a new scientific detection.

This README is a post-run report. It does not replace or amend frozen executable source, scope, claims, or receipts. The exact executed scope SHA-256 is `8f453c8d6eb96604fba658636d955093ad2b79d471e8c621e12c0aa39979291e`.

## Executed fixture and search

Six complete `(16, 12096)` little-endian float32 arrays were constructed once from a fixed integer counter hash, without an RNG API or random state. The prescribed base is `0.75 + low20bits * 2^-21`, followed by the exact float32 cast. Four-row stationary one-channel probes add raw power 2.0 at rows 6–9:

| Probe | Scans | Channel relative to core start | Intended behavior observed |
| --- | --- | ---: | --- |
| Matched diagnostic | `epoch1_on`, `epoch1_off` | 1024 | Recovered before OFF; rejected by OFF |
| Primary isolated probe | `epoch2_on` | 3072 | Recovered before and after OFF |

The primary truth declares only `epoch2_on`. The matched diagnostic has a separate truth and recovery object, since the two probes have different reference channels. The counter hash makes no statistical independence, Gamma noise, telescope noise, SNR calibration, or flux calibration claim.

The actual unchanged `detector.search_cadence` evaluated all six scans using the frozen scientific geometry: 4096 ON reference carriers; 6652 OFF reference carriers, including a 1278-channel halo on each side; all 5723 global drift-grid members; widths 1, 3, 9, and 33; and four-row windows starting at 0, 2, 4, 6, 8, 10, and 12. Original 4096-channel row normalization, nearest-edge median501 preprocessing, top-five native identity selection, complete OFF score-at-least-8 inventories, and discrete ANY-alias witness rules were retained.

| Scan | Role | Reference carriers | Original-grid hypotheses covered | Unique native hypotheses scored |
| --- | --- | ---: | ---: | ---: |
| `epoch1_on` | ON | 4096 | 656,359,424 | 579,452,928 |
| `epoch1_off` | OFF | 6652 | 1,065,943,088 | 760,696,112 |
| `epoch2_on` | ON | 4096 | 656,359,424 | 194,920,448 |
| `epoch2_off` | OFF | 6652 | 1,065,943,088 | 331,668,720 |
| `epoch3_on` | ON | 4096 | 656,359,424 | 472,334,336 |
| `epoch3_off` | OFF | 6652 | 1,065,943,088 | 941,045,136 |
| **Total** | | **32,244** | **5,166,907,536** | **3,280,117,680** |

Original-grid counts include discrete aliases represented by each scored native identity; they do not claim that identical aliases were redundantly scored. The producer and independent QA each traversed the complete declared family.

## Observed result and preserved payload

The actual output contains 481 retained ON threshold hypotheses: 388 were OFF matched and 93 survived the OFF comparison. The complete OFF inventories contain 737 records in `epoch1_off` and zero records in each of the other two OFF scans. The complete pre-OFF ON maximum is `22.572414703963005`.

Independent localization found 80 primary probe matches before OFF and the same 80 afterward. The matched diagnostic had 349 localized matches before OFF and zero afterward. These are hypothesis counts around two prescribed artificial probes, not counts of independent signals or astronomical candidates.

The unchanged `worker.json_and_array_store` produced 454 genuine numerical output fields. All 454 arrays and six original raw input arrays passed through the new payload, making 460 transported arrays with 29,623,468 total uncompressed logical array bytes. All 36 original normalization fields remained Python lists. Geometry, complete native alias tables, complete retained maps, all OFF records and certificates, ON hypotheses and witnesses, truth, recipe, engineering admission, and original descriptor keys, paths, shapes, dtypes, byte counts, and hashes were preserved.

The physical new payload is 8,589,276 bytes. Its semantic SHA-256 is `a3eee3568343ce58bc4821c08abfb14463e5e172a34cc8b1c4132281f12c5230`; its manifest SHA-256 is `54f4d7e7b5c983e08a54f099589320e69b688266980f519b93f7a38a78c712a8`.

## Independent QA and legacy consumer

The verifier independently reconstructed every raw byte using a separate two-dimensional implementation of the fixed counter arithmetic. It then used the unchanged `qa.decode`, `geometry`, `stream_search`, `verify_scan`, `verify_hits`, and `verify_recovery` functions. It did not import the producer's numerical fixture builder, detector, generator, old admission routine, or old study main.

QA passed **864,262 checks**, including all complete scan maps, every OFF record and hash, complete alias membership, all discrete OFF witnesses, normalization list types, original descriptors, input identities, and primary/diagnostic localization. Selected observed maximum absolute errors were:

| Quantity | Maximum absolute error |
| --- | ---: |
| Complete retained top-five scores | `1.4210854715202004e-14` |
| Full-core normalization | `2.862293735361732e-17` |
| Per-carrier maxima | `9.325873406851315e-15` |
| Complete OFF maxima | `3.552713678800501e-15` |
| Selected direct-cell sums versus prefix arithmetic | `2.398081733190338e-14` |
| Every OFF threshold score and actual OFF witness | `0` |
| Global pre-OFF ON maximum, whole drift grid, midpoint coordinates | `0` |

The unchanged QA tolerances were retained: normally `1e-10` for numerical comparisons, `1e-9` for selected direct-cell sums versus prefix arithmetic, and exact equality or zero tolerance where explicitly prescribed. The largest observed numerical discrepancy was `2.398081733190338e-14`.

The summary phase wrote genuine `inputs.npz` and `maps.npz` projections one array at a time from the authenticated new payload. An explicit provenance bridge added only the legacy completion envelope: `status`, `data_integrity_ok`, `resource_receipt`, and `array_store`. Resource values came from the producer's exact completed parent `wait4` receipt. No original result field was overwritten. The unchanged `summarize.case_record(..., require_qa=True)` authenticated the full manifest and returned `VALID_CASE` for this engineering projection. The summary independently reconciled the actual hit, OFF survivor, maximum, and localized recovery censuses.

That `VALID_CASE` means legacy file-format and consumer interoperability within the new engineering namespace. It does not admit a scientific study or bank.

## Whole-process resources and phase accounting

Every child was launched and reaped once by the pinned whole-child guard. All three exited with code 0, passed the parent resource gate, and had no watchdog firing. The ledger closed with eight immutable events, all three reserved slots accepted, no pending claims, and no refunded reservations.

| Phase | Complete child CPU, seconds | Parent wall time, seconds | Peak RSS, bytes | Peak RSS, MiB | CPU / wall / address-space caps |
| --- | ---: | ---: | ---: | ---: | --- |
| Producer | 143.410664 | 143.432681126 | 93,609,984 | 89.2734375 | 600 s / 1800 s / 1 GiB |
| Independent QA | 106.935669 | 106.955337383 | 99,442,688 | 94.8359375 | 600 s / 1800 s / 1 GiB |
| Legacy consumer and summary | 1.678944 | 1.683577351 | 46,870,528 | 44.69921875 | 120 s / 300 s / 1 GiB |
| **Total measured child CPU** | **252.025277** | | | | |

The whole prospective CPU reservation was 1400 seconds: 600 + 600 + 120 for the three children, plus 80 for metadata and delivery. The output ledger retained 1,749,024,768 reserved bytes under a 2,147,483,648-byte total limit. The actual output tree measured 19,746,365 bytes immediately before the final result receipt. Producer payload writing was physically capped at 768 MiB; phase payload allowances were 800 MiB, 64 MiB, and 800 MiB. Python child logs were bounded; native descriptor writes remained a post-reap size acceptance check, not a universal hard log-writer quota.

The ledger's `exposed` phase name was used only for the engineering legacy-format projection. This phase did not read telescope data or perform an exposed observation search.

## Evidence and limits

Authoritative execution evidence is in `work/SETI_FULLSEARCH_PAYLOAD_ENGINEERING_20261016_V1/`: `FROZEN_SCOPE.json`, `fixture/PRODUCER.json`, `QA_REPORT.json`, `SUMMARY_REPORT.json`, `RESULT.json`, the three `process_*/WAIT4_RECEIPT.json` files, and the closed `ledger/` event chain. Complete payload arrays and metadata remain in `fixture/payload/`; genuine legacy-format consumer artifacts remain in `summary_projection/`.

This is an observed full-case integration pass for the fixed fixture, including a nonempty complete OFF inventory and real matched and surviving ON hypotheses. It is not a successful stress test at the permitted two-million-record cap in every OFF scan, nor a guarantee that every permitted case fits the resource caps. It establishes no scientific-bank admission, sensitivity, physical or telescope false-alarm probability, new sky result, or qualified SETI detection. No independent 63-case calibration panel was produced or consumed; rank status is **`NOT_APPLIED_NO_CALIBRATION`**, and no rank or statistical final-candidate classification was applied. Original A/B remains `FAIL_CLOSED`.

The completed work implements and verifies the transport, independent QA, resource accounting, and full-case consumer pipeline around the existing detector. It does not introduce a new detector or alter the scientific search family.
