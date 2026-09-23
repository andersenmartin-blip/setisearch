# LS8AY — GJ 536 complete signed set and image metadata

23 September 2026. **FROZEN BEFORE CAL/COR HEADERS, METADATA OR PIXELS**.
Audited LS8AX source: `a5e343f7b5b6fee73514f2d06bda8e2b64feb85b`.

The rank-20 pair supplied 4,254 rows and 10,215 eligible overlapping windows.
The first visit has 32 positive crossings in seven clusters and five negative
crossings in one cluster; the second has six positive crossings in one cluster.
All 122,580 independent comparisons pass, with zero disagreements. All 68 new
LS8AX files match their public Git identities locally; 28 header and 22 L2
manifest entries pass SHA256. The full figure was visually inspected. The
initial checkout timeout, which read zero archive bytes, remains documented.
Scores are not Gaussian significances; overlapping windows are not independent.

| Representative | Sign | Start row, zero-based | Event rows | Context [start,stop) | Score |
|---|---|---:|---:|---|---:|
| TG023501_P0 | positive | 1816 | 1 | 1802:1831 | +18.968233631134098 |
| TG023501_P1 | positive | 1849 | 1 | 1835:1864 | +9.877824201573643 |
| TG023501_P2 | positive | 2573 | 1 | 2559:2588 | +13.572894443592835 |
| TG023501_P3 | positive | 2770 | 1 | 2756:2785 | +31.864099484625267 |
| TG023501_P4 | positive | 3082 | 1 | 3068:3097 | +20.039903364471826 |
| TG023501_P5 | positive | 3323 | 1 | 3309:3338 | +15.723832564690060 |
| TG023501_P6 | positive | 3408 | 1 | 3394:3423 | +2923.687794814556600 |
| TG023501_N0 | negative | 802 | 1 | 788:817 | -14.861686433842399 |
| TG007801_P0 | positive | 17 | 1 | 3:32 | +47.629871839031360 |

This is the complete signed set from both original visits: eight positive,
one negative. The first eight are in CH_PR100011_TG023501_V0300 and each
lasts 40.1699981689453 seconds; the last is in CH_PR100018_TG007801_V0300
and lasts 40.2000007629395 seconds. All have NEXP=1. The nine contexts are
disjoint within each visit and contain **261 rows**. All original EVENT and
context EVENT OR values are zero; they supply no new veto. No extra point,
comparison, aperture or visit is selected, including visible excluded points.

## Metadata only

Pin current manifests/summary/audit and unchanged image mathematics, metadata
reader, independent audit and timeout helper in config/ls8ay_representatives.json.
Require public freeze HEAD, clean tracked tree and matching pins before access.
Acquire only these two visits' SCI_CAL_SubArray and SCI_COR_SubArray headers
and their SCI_CAL_ImageMetadata / SCI_COR_ImageMetadata tables: four products.

Keep the **20,000,000-byte per-product budget**, checked before every range;
HTTP 206, exact range/length/total, stable ETag and exact filename. Skip image
and smearing arrays by declared FITS lengths. This stage reads zero pixels.
Preserve all headers, tables, receipts, failures and partial outcomes.
URL resolution retains the tested timeout-only helper: at most three identical
45-second calls, five-second spacing, serialized logging. Byte identity and
schema assertions are neither retried nor weakened.

Join all 261 context rows independently to CAL and COR: **522 unique joins**,
<=1 ms MJD/BJD tolerance, exact UTC text, agreeing exposure counters and
integrity. Do not assume L2 and image row indices are equal. Require matching
unscaled 200x200 float64 arrays, detector offsets and native units. Verify
PIPE_VER, NEXP, EXPTIME and TEXPTIME against each own L2 header, preserving
the two different cadences. Check COR smearing layout without reading values.
The independent struct decoder must pass before pixels; publish joins and
exact future ranges in config/ls8ay_images.json. Independent event_map,
regression, columns_projection and rebuild are AST-identical to LS8AR.

Use the verified sparse-checkout execution pattern, including every pinned
input and new output directory, with preservation conditional on checkout
success. No scientific scope or arithmetic changes.

## Conditional payload freeze and stopping

After metadata PASS, separately freeze the exact nine contexts and all CAL/COR
and smearing ranges. Keep the original common finite mask, 12-row sidebands,
two guards per side, C0/C1 conventions, r<=25 apertures, 30<r<=40 annuli,
column projection and r>35 smearing regression. Use native event sums at
the actual retained BJD times. Run all 11 inherited image tests before pixels.

Keep gate order: CORRECTION_LINKED (|DELTA/COR| or |column DELTA/COR|>=0.5
in both conventions, complete apertures and matching original sign), then
SPATIALLY_STRUCTURED (displacement explained energy>=0.8 and advantage>=0.2
over brightness in both), otherwise UNRESOLVED_WITHIN_FIXED_SCOPE.
Unavailable fits remain unavailable. Keep independent long-double/scalar
tolerances: relative 2e-8, native absolute 1e-6, dimensionless absolute 1e-8.

Inspect every representative's common-scale CAL/COR/DELTA figure. Stop after
all nine representatives. If all close, close this pair and prepare rank-21
2MASS J11285624+1010395 under separate header/table freezes. If any remain
unresolved, state the specific limitation before at most one separately frozen
study using retained data only. No extra pixels or visits to force closure;
the other three eligible GJ 536 visits remain outside the selected pair.

These descriptive labels identify neither a unique cause nor artificial
origin. No candidate, detector, significance, sensitivity or coverage is
qualified. Earlier labels, unassessed points, closed studies and reserved
TESS/M43 panels remain unchanged. Calibration NOT_READY; request UNSENT.
Publication is already authorized; delegation remains deferred.
