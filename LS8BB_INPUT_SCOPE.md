# LS8BB — complete signed 2MASS J11285624+1010395 set and image metadata

23 September 2026. **FROZEN BEFORE CAL/COR HEADERS, METADATA OR PIXELS**.
Audited LS8BA source: `f2fd067eec26e3d3b3002e14c3c2e616f8433675`.

The predetermined rank-21 pair supplied 97 retained rows. The first visit has
90 eligible overlapping windows, six positive crossings in one cluster and
three negative crossings in one cluster. The second visit has **zero eligible
windows**: it supplies no testable null result. All 1,080 independent L2
numerical/discrete comparisons pass without disagreement; both visits' context
enumerations and signed counts are checked. All 64 new LS8BA files have public
identities; the header and L2 manifests pass locally, and the full retained
figure has been visually inspected. Scores are not Gaussian significances.

| Representative | Sign | Event row, zero-based | Duration | Context [start,stop) | Score |
|---|---|---:|---|---|---:|
| TG010801_P0 | positive | 25 | 1 row / 60 s | 11:40 | +65.27745565007069 |
| TG010801_N0 | negative | 24 | 1 row / 60 s | 10:39 | -35.043142304664585 |

Both are in CH_PR100018_TG010801_V0300 and are the **complete signed set**.
The events are adjacent. Their 29-row contexts overlap in 28 rows, giving
58 context-row occurrences but only 30 distinct exposures (rows 10–39).
Both native events lie in the other's original guard rows, so neither is
included in the other's sideband baseline. Keep both contexts and their
original separate fits; do not merge events, masks or windows. They are not
independent observations. Original event/context EVENT OR values are zero
and supply no additional veto. Retained large edge points are not reselected.

## Metadata only

Pin both original visits' complete manifests/summary/audit and unchanged image
mathematics, metadata reader, independent auditor and timeout helper in
config/ls8bb_representatives.json. Derive and check the complete signed list
from both visits before access. Only the first visit has representatives:
acquire its SCI_CAL_SubArray / SCI_COR_SubArray headers and the corresponding
SCI_CAL_ImageMetadata / SCI_COR_ImageMetadata tables, **two source products**.
No image product from the zero-eligible second visit is opened.

Require public freeze HEAD, clean tracked tree and matching input pins.
Retain the 20,000,000-byte per-product budget checked before each range,
HTTP 206, exact range/length/total, stable ETag and exact key/filename.
Skip every image and smearing array by declared FITS lengths. **Zero pixels**
are read in this stage. Retain all headers, tables, receipts and partial
failures. URL resolution uses the unchanged timeout-only helper: at most
three identical 45-second calls, five-second spacing and serialized logs.
No identity/schema assertion is retried or relaxed.

Join each context row independently to CAL and COR, **116 join occurrences
covering 60 distinct CAL/COR exposure rows**. Each individual lookup must
have exactly one match within 1 ms MJD/BJD and exact UTC text, with agreeing
exposure counters and integrity. Overlap between contexts is retained and
is not misreported as 116 distinct exposures. Do not assume image/L2 indices
are equal. Require matching unscaled 200x200 float64 image layouts, native
units and detector offsets. Verify pipeline, NEXP, EXPTIME and TEXPTIME
against the first visit's own L2 header (1, 60, 60; pipeline 14.1.2).
Check smearing layout without values. Publish every join and exact future
range in config/ls8bb_images.json; independent struct decoding must pass
before any pixel access.

The independent event_map, regression, columns_projection and rebuild
functions are AST-identical to LS8AY. Only provenance, paths, keys and fixed
counts change. Use the existing sparse-checkout execution pattern, with all
required inputs and outputs and preservation conditional on successful
checkout. Scientific arithmetic and tolerances remain unchanged.

## Conditional payload freeze and stopping

After metadata PASS, separately freeze both complete contexts and exact
CAL/COR/smearing ranges before pixels. Retain repeated bytes where the
original contexts overlap; do not count the duplicates as independent data.
Keep the original common finite mask, 12-row sidebands, two guards per side,
C0/C1 conventions, r<=25 apertures, 30<r<=40 annuli, column projection and
r>35 smearing regression. Use native event sums at retained BJD times.
Run all 11 inherited image tests before pixels.

Retain gate order: CORRECTION_LINKED (absolute DELTA/COR or column DELTA/COR
>=0.5 in both conventions, complete apertures and matching original sign),
then SPATIALLY_STRUCTURED (displacement explained >=0.8 and advantage over
brightness >=0.2 in both), otherwise UNRESOLVED_WITHIN_FIXED_SCOPE.
Unavailable fits remain unavailable. Independent long-double/scalar
tolerances remain relative 2e-8, native absolute 1e-6, dimensionless 1e-8.

Inspect both representatives' common-scale CAL/COR/DELTA figures. Stop after
both signed events. If both close, close this pair and prepare rank-22 GJ 422
under separate header/table freezes. If any remains unresolved, state the
specific limitation before at most one separately frozen retained-data-only
study of the complete unresolved set. No extra pixels or visits to force
closure. Descriptive labels establish neither a unique cause nor artificial
origin. No candidate, detector, significance, sensitivity or coverage is
qualified. Prior labels, unassessed points, closed studies and reserved
TESS/M43 panels remain unchanged. Calibration NOT_READY; request UNSENT.
Standing publication authorization applies; delegation is deferred.
