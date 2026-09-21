# LS8AB — WASP-43 complete signed representative set and image metadata

21 September 2026. **FROZEN BEFORE NEW CAL/COR HEADERS, METADATA OR IMAGES**.

Audited LS8AA result: `ae3c8841cb3575c8008f5c85245448ac8b833d16`.
The 271 rows provide 294 eligible overlapping windows: **one positive crossing
in one positive cluster**, zero negative crossings. Both stable-arithmetic
tests and 3,528 independent numerical/discrete comparisons pass. All 22 result
files were checksum verified; the L2 figure was visually inspected before
this follow-up.

| Exact visit | Sign | Cluster | Start row, zero-based | Duration | Score | Context [start,stop) |
|---|---|---:|---:|---|---:|---|
| CH_PR100016_TG007801_V0300 | positive | 0 | 62 | 1 row / 60 s | +9.486349813911296 | 48:77 |

This is the complete signed representative set. The second selected visit,
CH_PR100016_TG007802_V0300, has no crossing and requires no images. Check
both visits' positive and negative lists against the frozen configuration
before access. Do not add below-threshold comparisons or substitute another
representative. The score is not Gaussian sigma. Event and context EVENT OR=0
remain metadata, not a new veto. No qualified SETI candidate is claimed.

## Metadata-only scope

Pin the complete LS8AA header/screen manifests, summary and audit, metadata
reader, unchanged image mathematics, prior LS8T/LS8Z audit source and tested
URL-timeout helper. Require public freeze HEAD, a clean tracked tree and
matching pins before access. Read only the exact first visit's
SCI_CAL_SubArray and SCI_COR_SubArray headers and corresponding
SCI_CAL_ImageMetadata and SCI_COR_ImageMetadata tables.

Keep the **20,000,000-byte budget per product**, checked before every range.
Require HTTP 206, exact ranges/lengths, stable total size and ETag and exact
filename. Preserve all headers, tables, receipts and partial results. Skip
image and smearing arrays by declared FITS lengths; this stage permits
**zero image pixels**. No second-visit images, other aperture, later visit
or raw imagette is included.

Reuse the tested URL-timeout helper unchanged: at most three identical
resolution requests per product, original 45-second timeout, five-second
spacing, retry only TimeoutError or that exact wrapped URLError reason.
Serialize concurrent log writes and omit temporary URLs. Byte requests,
identity and schema assertions are not retried or weakened.

Join all **29 original L2 context rows** separately to CAL and COR:
**58 unique joins**, <=1 ms MJD/BJD differences, exact UTC text and agreeing
exposure counters/integrity. Do not assume row-index equality. Check unscaled
200x200 float64 image arrays, matching offsets/BUNIT and equality to L2
PIPE_VER=14.1.2, NEXP=1 and EXPTIME=TEXPTIME=60 seconds. Verify the COR
smearing-row layout without reading values.

The independent struct-decoder audit must pass before pixels. Its event-map,
regression, column-projection and rebuild functions are AST-identical to
LS8Z/LS8X/LS8T. Publish joins, exact source identities and future ranges in
config/ls8ab_images.json, retaining zero image bytes. Any mismatch is preserved
and stops the stage without changing inputs, joins or tolerances.

## Conditional image stage after a separate payload freeze

After metadata/audit PASS, separately freeze exact image/smearing ranges,
dependency hashes and the unchanged paired-image diagnostic. Keep the common
finite mask, 12-row sidebands, two-row guards, C0/C1 conventions, r<=25 apertures,
30<r<=40 annuli and original column/smearing diagnostics. The positive remains
one 60-second exposure. Preserve gate order: CORRECTION_LINKED,
SPATIALLY_STRUCTURED, otherwise UNRESOLVED_WITHIN_FIXED_SCOPE, with complete
apertures and COR/L2 sign agreement in both conventions. Run all nine inherited
synthetic tests before pixels; retain the independent long-double/scalar audit
and unchanged tolerances. No extra masks, weights or hypothetical subtraction.

Stop after the original representative. If it closes under the fixed gates,
close WASP-43 and prepare rank-9 PG1303-114 with separate header/table freezes.
If unresolved, state the remaining limitation before one separately frozen
retained-data diagnostic. No additional pixels or visits to force closure.
Labels do not establish a unique physical cause or artificial origin. No
detector, candidate or observing coverage is qualified. Prior unresolved
events and bounded studies are unchanged; reserved TESS/M43 panels stay closed.
Calibration is NOT_READY, its request unsent, publication already authorized.
Delegation remains deferred.
