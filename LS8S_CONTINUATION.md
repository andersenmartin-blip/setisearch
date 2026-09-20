# Continue after LS8S

The independent **rank-4 TESS_260647166** DEFAULT-L2 screen is complete and
independently audited. Result commit:
`cc05ba9a55a98bcfe6e1c747820ec4dd3265617f`.
The target name refers to CHEOPS products; no reserved TESS sector was opened.

## Complete signed result

| Visit | L2 rows | Exposure per row | Eligible overlapping windows | Positive crossings / clusters | Negative crossings / clusters |
|---|---:|---:|---:|---:|---:|
| CH_PR300046_TG000101_V0300 | 983 | 42 s | 1,005 | 0 / 0 | 2 / 1 |
| CH_PR100031_TG015701_V0300 | 764 | 49 s | 999 | 6 / 1 | 0 / 0 |
| Total | 1,747 | Visit-specific | 2,004 | 6 / 1 | 2 / 1 |

The six positive windows overlap one event and form **one positive cluster**;
they are not six separate detections. Both negative windows form one negative
cluster. Retain both original representatives and every cluster member:

| Representative | Sign | Zero-based event rows | Integrated exposure | L2 score |
|---|---|---|---:|---:|
| TG000101_N0 | negative | 317–319 | 3 × 42 = 126 s | -10.085104590 |
| TG015701_P0 | positive | 217 | 49 s | +45.460348286 |

NEXP=1 in both visits. The unchanged screen tested 42/84/126-second sums in
the first visit and 49/98/147-second sums in the second, using each visit's
verified TEXPTIME for cadence eligibility. Both representatives and contexts
have EVENT OR=0; this remains reported metadata rather than an extra veto.

## Prospective scope and verification

The target and its first two eligible visits remain fixed by the reconciled
LS8J chronological ledger, ranked by second eligible visit, then first visit
and target name. The seven-visit cohort was not reordered or widened. The
original missing full-inventory-response limitation and separately dated
complete reconciliation remain recorded.

The metadata-only freeze acquired 40,320 header bytes and no table values,
verifying both exposure tuples and the common 18-field/138-byte schema.
A separate science freeze then acquired exactly **241,086 table bytes**
under exact range, filename, ETag and total-size checks.

The stable LS8K scorer and independent auditor remain hash-pinned and
unchanged: original whole-context eligibility, 12 sideband rows and two
guards each side, flux-centered local linear baseline, robust/formal noise,
prediction leverage, ±8.5 endpoints and signed cluster representation.
Earlier residual diagnostics and image classifications are not new cuts.

Both stable-arithmetic known-answer tests pass. The independent struct/scalar
audit passes **24,048 numerical/discrete comparisons**, with zero numerical
disagreements at the original relative 2e-8 / absolute 2e-10 tolerances.
The full L2 figure and local review files match the immutable checksum
manifest; the figure has been visually inspected with all eligible scores
and the complete retained light curves, including flagged rows for context.

The positive score is **not a Gaussian significance** or calibrated
false-alarm probability. Windows overlap and are not independent trials.
The result establishes neither artificial origin, a qualified candidate or
detector, sensitivity to shorter glints, completeness, population limits
nor additional qualified observing coverage.

## Both signs proceed to the image diagnostic

Both TG000101_N0 and TG015701_P0 enter **LS8T**, with all 60 original context
rows preserved. The negative three-exposure event is not replaced by a
shorter representative, and the positive is not followed in isolation.
Metadata joins precede the exact image/smearing payload freeze.

The image results, any concrete remaining limitation and active next action
are in **[LS8T_CONTINUATION.md](LS8T_CONTINUATION.md)**. Do not widen the pair,
add an aperture or change thresholds based on its score or appearance.
Closed HD 136352/GJ 1132/WASP-189 studies, raw imagettes and reserved TESS/M43
data remain unchanged. The separate calibration request remains unsent.

[L2 report and figure](results_ls8s_l2_screen/REPORT.md) ·
[Independent audit](results_ls8s_l2_screen/audit.json) ·
[Header protocol](LS8S_TESS260647166_HEADER_PROTOCOL.md) ·
[Exact L2 protocol](LS8S_TESS260647166_L2_PROTOCOL.md) ·
[Publication identities](PUBLICATION_2026-09-20_LS8S_LS8T.md).
