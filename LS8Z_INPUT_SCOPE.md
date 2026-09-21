# LS8Z — PG 1245-042 complete signed representative set and image metadata

21 September 2026. **FROZEN BEFORE NEW CAL/COR HEADERS, METADATA OR IMAGES**.

Audited LS8Y result: `588398eacf6316324d24954150b57e69422f2d0a`.
The 164 rows provide 228 eligible overlapping windows: zero positive
crossings and **four negative crossings in one negative cluster**. Both
stable-arithmetic tests and 2,736 independent numerical/discrete comparisons
pass. All 22 result files were checksum verified; the L2 plot was visually
inspected before this follow-up.

| Exact visit | Sign | Cluster | Start row, zero-based | Duration | Score | Context [start,stop) |
|---|---|---:|---:|---|---:|---|
| CH_PR100002_TG008601_V0300 | negative | 0 | 31 | 1 row / 60 s | -18.490171716816285 | 17:46 |

This is the complete signed representative set. The second selected visit,
CH_PR100002_TG008602_V0300, has no crossing and requires no images. Check
both visits' positive and negative lists before acquisition; no below-threshold
comparison or replacement representative is included. The score is not
Gaussian sigma. EVENT OR=0 for event and context is retained as metadata,
not used as a new veto. A negative event is followed under the same original
signed diagnostic; it is not a qualified SETI candidate.

## Metadata-only scope

Pin complete LS8Y header/screen manifests, summary and audit, the metadata
reader, unchanged image mathematics, prior LS8T/LS8X audit source and tested
URL-timeout helper. Require public freeze HEAD, clean tracked tree and
matching pins before access. Read only the exact first visit's
SCI_CAL_SubArray and SCI_COR_SubArray headers and corresponding
SCI_CAL_ImageMetadata and SCI_COR_ImageMetadata tables.

Keep the existing **20,000,000-byte budget per product**, checked before
every transfer. Require HTTP 206, exact ranges/lengths, stable total size
and ETag and the exact filename. Preserve every header, table, receipt and
partial result. Skip image/smearing arrays by declared FITS lengths. This
stage permits **zero image pixels**. No second-visit image, later visit,
other aperture or raw imagette is included.

Reuse the tested URL-resolution helper unchanged: at most three identical
requests per product, 45-second timeout, five-second spacing, retry only
TimeoutError or that exact wrapped URLError reason. Serialize concurrent
log writes; retain outcomes without temporary URLs. Byte requests and
identity/schema assertions are not retried or weakened.

Join all **29 original L2 context rows** separately to CAL and COR:
**58 unique joins**, <=1 ms MJD/BJD differences, exact UTC text and agreeing
exposure counters/integrity. Do not assume row-index equality. Check unscaled
200x200 float64 images, matching offsets/BUNIT and equality to the L2
PIPE_VER=14.1.2, NEXP=1 and EXPTIME=TEXPTIME=60 seconds. Check the COR
smearing-row layout without reading values.

The independent struct-decoder audit must pass before pixels. Numerical
image-reconstruction functions are AST-identical to LS8X/LS8T. Publish
joins, source identities and exact future intervals in config/ls8z_images.json,
with zero image bytes. Preserve any mismatch and stop without changing
products, joins or tolerances.

## Conditional image stage after a separate payload freeze

After metadata/audit PASS, separately publish exact image/smearing ranges,
dependency hashes and the unchanged paired-image diagnostic. Keep common
finite masks, 12-row sidebands, two-row guards, both C0/C1 conventions,
r<=25 apertures, 30<r<=40 annuli and original column/smearing diagnostics.
The negative remains one 60-second exposure. Preserve gate order:
CORRECTION_LINKED, SPATIALLY_STRUCTURED, otherwise
UNRESOLVED_WITHIN_FIXED_SCOPE. Require complete apertures and COR/L2 sign
agreement in both conventions. Run all nine inherited synthetic tests
before payload and keep the independent long-double/scalar audit and
unchanged numerical tolerances. No new masks, weights or subtraction cuts.

Stop after the original representative. If it closes under the fixed
descriptive gates, close PG 1245-042 and prepare rank-8 WASP-43 with separate
metadata/science freezes. If unresolved, state the specific remaining
limitation before one separately frozen retained-data diagnostic. Do not
open additional frames or visits to force a classification. Labels do not
establish a unique physical cause or artificial origin. No candidate,
detector or observing coverage is qualified. Other closed studies and prior
unresolved events remain unchanged; reserved TESS/M43 data stay closed.
Calibration is NOT_READY and its request unsent. Publication is authorized;
delegation remains deferred.
