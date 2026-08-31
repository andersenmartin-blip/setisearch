# Milestone 37 v0.6.1 complete spectral retention

Status: **ON/OFF RETENTION COMPLETE — PHYSICAL AND STATISTICAL ADJUDICATION
PENDING; NO SIGNAL OR NULL CLAIM**.

The post-contact capacity-only amendment was executed in a new run. It changed
resource envelopes only: the threshold, proxy grid, template bank, widths,
activity subsets, score statistic and veto definitions remain unchanged.

## Run lineage

Run 005 stopped before cache access because the first calibration-adoption
validator incorrectly required byte-identical factor-bundle manifests. Those
manifests contain run-specific provenance even when their scientific arrays
are identical. Run 005 was permanently invalidated at journal head
`f6393219…`; it read no spectral dataset values.

Run 006 instead requires exact equality of the run-independent factor basis,
basis labels, factor table, template bank, scan definitions and analysis
contract. It also requires the new and source cache manifests to contain the
same 240-entry inventory and re-hashes every immutable cache payload.

| Reused input | Result |
|---|---:|
| Cache entries | 240 |
| Cache payload bytes | 11,545,072,128 |
| Cache inventory SHA-256 | `50de36cb3c1f6a78f0f81d0c0deda050d6a3e10774543b5227c77c1d96e7a313` |
| Verified inventory SHA-256 | `3bc5e5c745043cb5d738b85a89c9f4e8b5917c842c48f32b83f8e8ee43774c97` |
| Calibration-adoption SHA-256 | `221056fc7cf47c8ac528ed6aad57558dbfadabe6ee47dcc7e7c338f27dc3e21e` |
| Threshold certificate SHA-256 | `d65048bd962a247a3763eb58c9cad530d9f7db06586f52a01a34e03b4ba0ad71` |
| Operational threshold S/N | 126.20158386230469 |

The exact sealed Run 004 calibration and global null were adopted rather than
recomputing 2,848,065,331,200 null score cells after spectral contact.

## Complete normative retention

Four independent processes evaluated all 2,976 hypotheses and all
2,225,051,040 score cells for each window/kind pair. Unlike the census, this
pass produced the complete canonical records, replay hashes, record chains and
retention certificates.

| Window | ON records | OFF records |
|---|---:|---:|
| `m37_1400p5` | 1,800 | 1,720 |
| `m37_1406p5` | 218 | 232 |
| `m37_1412p5` | 225 | 208 |
| `m37_1418p5` | 41,640 | 0 |
| `m37_1425p0` | 0 | 0 |
| **Total** | **43,883** | **2,160** |

Every count exactly reproduces the separately sealed capacity census. The
largest window remains 8,360 records below the amended 50,000-record limit;
no truncation or threshold adaptation occurred. A restart reopened all ten
artifacts and their independent receipts without changing the journal.

The complete ledgers are preserved as deterministic gzip files under
`results_m37_v0p6p1_primary_006/retention/`; their decompressed SHA-256 values
are the file receipts in the ON and OFF inventories.

## Interpretation boundary

The spectral search and ON/OFF retention are now complete, but 43,883 ON
records are not 43,883 independent candidates. In particular, the 41,640
records at 1418.5 MHz are a dense 129-channel score-space feature repeated
over neighboring carrier cells, motion templates and activity subsets.

No record has yet received the frozen same-hypothesis OFF, local OFF,
single-adjacent-OFF or receiver-frame alias disposition, and global rank
significance has not been joined. Run 006 therefore supports neither a signal
claim nor a null claim. Its current journal stage is `off_retention_complete`
with head `4e67cea9…`. The next work item is complete physical disposition,
followed by rank significance and final outcome assembly.
