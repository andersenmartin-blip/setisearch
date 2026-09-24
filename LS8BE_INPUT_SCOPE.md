# LS8BE — complete signed GJ 494 set and paired-image metadata

24 September 2026. **FROZEN BEFORE NEW CAL/COR HEADERS, METADATA OR PIXELS**.
Audited LS8BD source: `a5a3fd0e1678c2e77d505d9fac209e1cba55f9a9`.

The rank-23 chronological first pair supplies 148 retained rows and 165
eligible overlapping windows. First visit: 117 windows, two positive
crossings forming one cluster, no negative crossings. Second visit: 48
windows with neither sign crossing. The independent audit passes all 1,980
comparisons and both signed-cluster/count checks. All header and L2 manifest
entries pass locally, and the complete L2 figure has been visually inspected.
Scores are not Gaussian significances. The two later visits stay closed.

The **complete signed representative set** has exactly one member:

| Representative | Exact visit | Sign | Event row, zero-based | Duration | Context [start,stop) | Score |
|---|---|---|---:|---|---|---:|
| TG007401_P0 | CH_PR100018_TG007401_V0300 | positive | 53 | 1 row / 42 s | 39:68 | +17.588818768661 |

EVENT and context EVENT OR are zero and add no veto. Preserve both original
cluster members and the selected strongest representative; do not open
second-visit images or substitute a large ineligible point. The 29 context
rows are distinct exposures, yielding 58 CAL/COR exposure joins with no
overlapping representative contexts.

## Metadata only

Pin both visits' complete original manifests, summary and audit together
with unchanged image mathematics, metadata reader, independent auditor and
timeout helper in config/ls8be_representatives.json. Derive the complete
signed list from both visits and verify it before any new access. Acquire
only the first visit's SCI_CAL_SubArray / SCI_COR_SubArray headers and
SCI_CAL_ImageMetadata / SCI_COR_ImageMetadata tables: two products.

Require public freeze HEAD, clean tracked checkout and matching input pins.
Keep the 20,000,000-byte per-product metadata budget checked before each
range, HTTP 206, exact range/length/total, stable ETag and exact key/filename.
Skip all image and smearing arrays by declared FITS lengths; zero pixels
are authorized here. Preserve every header, table, receipt and partial
failure. Use the unchanged timeout-only URL resolver, at most three identical
45-second calls with five-second spacing and serialized logs. Identity or
schema assertion failures are neither retried nor relaxed.

Independently match each context row to CAL and COR: exactly one match
within 1 ms in MJD/BJD and exact UTC text, agreeing exposure counters and
integrity. Do not assume image/L2 row indices coincide. Verify matching
unscaled 200x200 float64 layouts, native units and detector offsets, plus
each product's NEXP, EXPTIME, TEXPTIME and pipeline against its own L2
header (1, 42, 42 seconds; 14.1.2). Inspect the declared smearing layout
without values. Publish all 58 joins and exact future ranges in
config/ls8be_images.json; independent struct decoding must pass before pixels.

The independent event_map, regression, columns_projection and rebuild
functions remain AST-identical to LS8BB. Only provenance, paths, keys and
fixed counts change. Retain the established sparse checkout with all
required inputs/outputs and preservation conditional on checkout success.

## Conditional payload freeze and stopping

After metadata PASS, separately freeze the entire context and exact
CAL/COR/smearing ranges before pixels. Keep the common finite mask,
12-row sidebands, two guards per side, C0/C1 centers, radius-25 apertures,
30<r<=40 annuli, column projection and r>35 smearing regression. Retain
native event sums at the actual BJD times. Run all 11 inherited image tests
before pixels. Preserve the fixed gate order:

1. CORRECTION_LINKED: absolute DELTA/COR or column-DELTA/COR >=0.5 in both
   conventions, with complete apertures and matching original COR/L2 sign.
2. SPATIALLY_STRUCTURED: COR displacement explained >=0.8 and its advantage
   over brightness >=0.2 in both conventions, subject to the same prerequisites.
3. Otherwise UNRESOLVED_WITHIN_FIXED_SCOPE.

Unavailable fits remain unavailable. Independent long-double/scalar
tolerances stay relative 2e-8, native absolute 1e-6 and dimensionless 1e-8.
Inspect the common-scale CAL/COR/DELTA figure. Stop after this complete
representative set. If it closes, close the pair and prepare rank-24
2MASS J11474440+0048164 under separate header/table freezes. If unresolved,
state the concrete limitation before at most one separately frozen,
retained-data-only study of the entire unresolved set. Do not acquire extra
pixels/visits to force closure. Labels establish neither a unique cause
nor an artificial origin. No candidate, detector, significance, sensitivity
or observing coverage is qualified. Prior labels, unassessed points, closed
studies and reserved TESS/M43 panels stay unchanged. Calibration NOT_READY;
request UNSENT. Publication authorized; delegation deferred.
