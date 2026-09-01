# Milestone 37 v0.6.1 physical, significance and outcome result

Status: **PRIMARY-CADENCE SEARCH CLOSED — NO UNRESOLVED SCIENTIFIC
CANDIDATES; NO TECHNOSIGNATURE CLAIM**.

Run `m37-v0p6p1-primary-006` completed the two adjudication stages frozen after
retention. Every one of the 43,883 retained ON records received a complete
physical disposition, an independent inclusive global rank-p item and one
final outcome record. The exact five-window join contains zero unresolved
scientific candidates and reports
`closed_no_unresolved_scientific_candidates`.

This is the M37 null outcome for the one selected HD 156668 archive cadence,
five frozen frequency windows, detector bank and interference controls. It is
not evidence that no transmitter exists, does not resolve the separate
Milestone 33 case, and does not yet supply a measured completeness or
population bound.

## Physical disposition

The physical pass reopened the exact 240-cache Run 006 inventory, streamed all
five windows under the 512 MiB mapped-array cap and assigned exactly one final
physical disposition per retained ON record.

| Window | Exact OFF | Local OFF | Adjacent OFF | Receiver alias | Unvetoed | Total |
|---|---:|---:|---:|---:|---:|---:|
| `m37_1400p5` | 1,115 | 548 | 137 | 0 | 0 | 1,800 |
| `m37_1406p5` | 75 | 61 | 82 | 0 | 0 | 218 |
| `m37_1412p5` | 128 | 93 | 4 | 0 | 0 | 225 |
| `m37_1418p5` | 0 | 0 | 41,640 | 0 | 0 | 41,640 |
| `m37_1425p0` | 0 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **1,318** | **702** | **41,863** | **0** | **0** | **43,883** |

The previously unexplained dense 1418.5 MHz score-space feature is therefore
not merely absent from retained OFF: every member has qualifying evidence in
the frozen single-adjacent-OFF control. No member survives to an unvetoed
physical state.

The physical pass opened 240 cache products in 80 bounded batches. Its largest
window peak was 144,319,872 mapped bytes across three handles, below the
536,870,912-byte cap.

## Independent global rank-p evidence

Rank-p was computed from the original retained ON records, before considering
their physical vetoes, against the exact sealed 256-member global-null vector.
The scientific empirical-p ceiling remained 0.01.

| Inclusive null exceedances | Inclusive rank-p | Records | Eligible |
|---:|---:|---:|---:|
| 0 | 0.0038910505836575876 | 5 | 5 |
| 1 | 0.007782101167315175 | 43,736 | 43,736 |
| 2 | 0.011673151750972763 | 142 | 0 |
| **Total** | — | **43,883** | **43,741** |

Statistical eligibility does not override a physical veto. All 43,741 eligible
records are physically vetoed, including all 41,510 eligible members in the
1418.5 MHz window. The remaining 142 records are both physically vetoed and
above the rank-p ceiling.

## Exact outcome join

The final join reopened each receiver-alias result, significance result and ON
retention receipt. It required identical record-ID sets, reconstructed the
retained-record bytes from every physical annotation and reproduced each
significance retained-record SHA-256 before applying veto precedence.

| Final disposition | Records |
|---|---:|
| `rfi_veto_matched_off_same_hypothesis` | 1,318 |
| `rfi_veto_local_off_track` | 702 |
| `rfi_veto_single_adjacent_off` | 41,863 |
| `rfi_veto_receiver_frame_alias` | 0 |
| `retained_but_not_scientifically_eligible` | 0 |
| `scientific_candidate_unresolved` | 0 |
| **Total** | **43,883** |

The 142 non-eligible members retain their earlier physical disposition; the
rank-p branch therefore does not replace or obscure physical evidence.

## Immutable identities

| Artifact | SHA-256 |
|---|---|
| Physical-disposition manifest file | `602a36eaff509c463275a4ab3dda79663ee4eeb40ca01b4ce3fe0d7777cb3bb5` |
| Physical-disposition manifest | `521de85e946c514e179fbb9bb530cd7031b0aadab4eb9c36297ed508382aeeda` |
| Physical child inventory | `bdb4553ba41bc509159c1e83c6abd107039b0d2a8b70e936d15f06ab3f83a738` |
| Significance manifest file | `978ca64e610e12bc00c7753c9303f594e25d9d5a035d351e4229340ba5bbe7af` |
| Significance manifest | `5b8cfe17f27a3ac05868cc8f71845bc24418c5402140027f76501245f3515d77` |
| Significance child inventory | `851beee16f9b4a2eb9bd41d785548c142689c6e64d06265b8e658e41f8965d2f` |
| Outcome file | `0dc06d5b8d743f9d8cc77ad48872a31775420f8eeb614eeca13d21007dfe0f4e` |
| Outcome result | `9ee6155ed77a89affab929c2ad3de2da10dd581463d57a3d331cd6dd12d8ebd3` |
| Outcome certificate | `6e16e2475aa5ab66dd444fcda787e5d586cdc693511b2d5ce9da7142be7a47e8` |
| Final journal head | `01488a0adc2167a5fc0e01f6038904885efb4bda2ac0123b9cb98f654021faa2` |

The large child and outcome files are stored as deterministic gzip. All file
receipts above identify their exact canonical decompressed JSON bytes. A full
restart reopened the compressed artifacts, regenerated every significance
item and reproduced the final outcome byte for byte without appending another
journal event.

## Verification and next boundary

The complete suite passed 306 tests with one expected benchmark skip and no
failures. The original v0.6 entry points remain bounded by their original
10,000-record/96,000,000-byte contracts; only the v0.6.1 adapters accept the
single sealed post-contact amendment.

The run journal now stops at `outcome_complete`. Detector completeness remains
a separate later stage. Until a complete injection replay is executed, this
result establishes candidate closure for the searched primary cadence but no
quantitative sensitivity or occurrence-rate constraint for Milestone 37.
