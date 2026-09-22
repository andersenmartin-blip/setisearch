# LS8AM — HD 106315 complete signed representative set and image metadata

22 September 2026. **FROZEN BEFORE NEW CAL/COR HEADERS, METADATA OR IMAGES**.

Audited LS8AL result: 36d081fac65ca35bccbfde5220660fd547d44bc9.
The 2,382 rows provide 4,698 eligible overlapping windows: 13 positive
crossings in three positive clusters and zero negative crossings. Both inherited
stable-arithmetic tests and 56,376 independent numerical/discrete comparisons
pass. All 22 result-manifest entries were locally checksum verified and all
62 new LS8AL scientific files match their published Git identities. The full
retained-table/score figure was visually inspected before this follow-up.

| Exact visit | Sign | Cluster | Start row, zero-based | Duration | Score | Context [start,stop) |
|---|---|---:|---:|---|---:|---|
| CH_PR100041_TG000801_V0300 | positive | 0 | 223 | 1 row / 41 s | +44.503884094991555 | 209:238 |
| CH_PR100041_TG000801_V0300 | positive | 1 | 363 | 1 row / 41 s | +9.691535552281110 | 349:378 |
| CH_PR100041_TG001401_V0300 | positive | 0 | 178 | 1 row / 41 s | +28.143188663326402 | 164:193 |

This is the complete signed representative set across both selected visits.
Check both visits' positive and negative lists against the frozen configuration
before access. All three representatives are individual 41-second exposures;
the context intervals are disjoint within each visit. Do not add below-threshold
comparisons or substitute other retained points that lack eligible context.
The score is not Gaussian sigma. Event and context EVENT OR=0 remain metadata,
not a new veto. No qualified SETI candidate is claimed.

## Metadata-only scope

Pin the complete LS8AL header/screen manifests, summary and audit, metadata
reader, unchanged image mathematics, prior LS8T/LS8AJ audit source and tested
URL-timeout helper. Require public freeze HEAD, a clean tracked tree and
matching pins before access. Read only the two exact selected visits'
SCI_CAL_SubArray and SCI_COR_SubArray headers and corresponding
SCI_CAL_ImageMetadata and SCI_COR_ImageMetadata tables.

Keep the **20,000,000-byte budget per product**, checked before every range.
Require HTTP 206, exact ranges/lengths, stable total size and ETag and exact
filename. Preserve all headers, tables, receipts and partial results. Skip
image and smearing arrays by declared FITS lengths; this stage permits
**zero image pixels**. No other aperture, visit or raw imagette is included.

Reuse the tested URL-timeout helper unchanged: at most three identical
resolution requests per product, original 45-second timeout, five-second
spacing, retry only TimeoutError or that exact wrapped URLError reason.
Serialize concurrent log writes and omit temporary URLs. Byte requests,
identity and schema assertions are not retried or weakened.

Join all **87 original L2 context rows** separately to CAL and COR:
**174 unique joins**, <=1 ms MJD/BJD differences, exact UTC text and agreeing
exposure counters/integrity. Do not assume row-index equality. Check unscaled
200x200 float64 image arrays, matching offsets/BUNIT and equality to L2
PIPE_VER=14.1.2, NEXP=1 and EXPTIME=TEXPTIME=41 seconds separately for every
product. Verify the COR smearing-row layout without reading values.

The independent struct-decoder audit must pass before pixels. Its event-map,
regression, column-projection and rebuild functions are AST-identical to
LS8AJ/LS8T. Publish joins, exact source identities and future ranges in
config/ls8am_images.json, retaining zero image bytes. Any mismatch is preserved
and stops the stage without changing inputs, joins or tolerances.

## Conditional image stage after a separate payload freeze

After metadata/audit PASS, separately freeze exact image/smearing ranges,
dependency hashes and the unchanged paired-image diagnostic. Keep the common
finite mask, 12-row sidebands, two-row guards, C0/C1 conventions, r<=25 apertures,
30<r<=40 annuli and original column/smearing diagnostics. All three positives
remain one 41-second exposure each. Preserve gate order: CORRECTION_LINKED,
SPATIALLY_STRUCTURED, otherwise UNRESOLVED_WITHIN_FIXED_SCOPE, with complete
apertures and COR/L2 sign agreement in both conventions. Run all nine inherited
synthetic tests before pixels; retain the independent long-double/scalar audit
and unchanged tolerances. No extra masks, weights or hypothetical subtraction.

Stop after all three original representatives. If they close under the fixed
gates, close the HD 106315 pair and prepare rank-14 WASP-103 with separate
header/table freezes. For any unresolved event, state the remaining limitation
before one separately frozen retained-data diagnostic. No additional pixels
or visits to force closure. HD 106315 has only these two eligible visits in
the original cohort. Labels do not establish a unique physical cause or
artificial origin. No detector, candidate or observing coverage is qualified.
Prior unresolved events and bounded studies are unchanged; reserved TESS/M43
panels stay closed. Calibration is NOT_READY, its request unsent, publication
already authorized. Delegation remains deferred.
