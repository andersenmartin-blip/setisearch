# LS8AR — GJ 581 complete signed set and image metadata

22 September 2026. **FROZEN BEFORE CAL/COR HEADERS, METADATA OR PIXELS**.
Audited LS8AQ source: 051d973dffe52f151f3948e38070b40bbc32cdf4.

The two rank-15 visits provide 3,623 rows and 7,869 eligible overlapping
windows. The first visit has 30 positive crossings in nine clusters and
16 negative crossings in five clusters; the second has zero signed crossings.
All 94,428 independent comparisons pass, with zero disagreements. All 62
new LS8AQ scientific files match their published Git identities; the 28 header
and 22 L2 manifest entries pass SHA256 checks. The retained-data figure was
visually inspected. Scores are not Gaussian sigma and windows are not independent.

| Representative | Sign | Start row, zero-based | Rows / duration | Context [start,stop) | Score |
|---|---|---:|---|---|---:|
| TG023701_P0 | positive | 1070 | 1 / 60 s | 1056:1085 | +10.117099458039316 |
| TG023701_P1 | positive | 2033 | 1 / 60 s | 2019:2048 | +11.029749181602263 |
| TG023701_P2 | positive | 2209 | 1 / 60 s | 2195:2224 | +15.415871544973099 |
| TG023701_P3 | positive | 2528 | 1 / 60 s | 2514:2543 | +61.514729501873468 |
| TG023701_P4 | positive | 2581 | 1 / 60 s | 2567:2596 | +15.370472148046623 |
| TG023701_P5 | positive | 2761 | 1 / 60 s | 2747:2776 | +29.757440687203143 |
| TG023701_P6 | positive | 2833 | 1 / 60 s | 2819:2848 | +9.187940675968894 |
| TG023701_P7 | positive | 3044 | 1 / 60 s | 3030:3059 | +11.554082508851558 |
| TG023701_P8 | positive | 3133 | 1 / 60 s | 3119:3148 | +59.493137161459714 |
| TG023701_N0 | negative | 975 | 1 / 60 s | 961:990 | -17.154258654577312 |
| TG023701_N1 | negative | 1511 | 2 / 120 s | 1497:1527 | -10.622953693161483 |
| TG023701_N2 | negative | 1587 | 1 / 60 s | 1573:1602 | -9.189141427759484 |
| TG023701_N3 | negative | 2679 | 1 / 60 s | 2665:2694 | -21.763188969336206 |
| TG023701_N4 | negative | 3264 | 1 / 60 s | 3250:3279 | -8.693767275408362 |

This is the complete signed set across both original visits, verified against
both positive and negative cluster lists before access. All representatives
are in CH_PR100011_TG023701_V0300. Thirteen are one 60-second exposure; N1
is two exposures summed over 120 seconds. The 14 contexts are disjoint and
contain 407 rows. EVENT/context EVENT OR=0 are metadata only. No other point,
comparison, visit or aperture is selected.

## Metadata only

Pin the LS8AQ manifests/summary/audit and unchanged image mathematics,
metadata reader and timeout helper in config/ls8ar_representatives.json.
Require public freeze HEAD, clean tracked tree and matching pins before access.
Acquire only the first visit's SCI_CAL_SubArray and SCI_COR_SubArray headers
and corresponding SCI_CAL_ImageMetadata / SCI_COR_ImageMetadata tables.
The second visit, CH_PR100018_TG008301_V0300, receives no image metadata
or pixels because it has no representative under the fixed eligibility rule.

Preserve the 20,000,000-byte per-product budget, checked before every range;
HTTP 206, exact range/length/total, stable ETag and exact filename. Skip image
and smearing arrays by declared FITS lengths. This stage reads zero pixels.
Preserve all headers, tables, receipts, failures and partial outcomes.
URL resolution retains the tested timeout-only helper: at most three identical
45-second requests, five-second spacing, serialized logging. Byte identity
and schema assertions are neither retried nor weakened.

Join all 407 context rows separately to CAL and COR: 814 unique joins,
<=1 ms MJD/BJD tolerance, exact UTC text, agreeing exposure counters and
integrity. Do not assume equality of L2 and image row indices. Require matching
unscaled 200x200 float64 image arrays, detector offsets and native units;
verify PIPE_VER=14.1.2, NEXP=1, EXPTIME=TEXPTIME=60 s against each L2 header.
Check the COR smearing layout without its values. The independent struct
decoder must pass before pixels; publish joins and exact future ranges in
config/ls8ar_images.json. Independent event_map, regression,
columns_projection and rebuild functions remain AST-identical to LS8AP/LS8T.

## Conditional payload freeze and stopping

After metadata PASS, separately freeze the exact 14 contexts and all CAL/COR
and smearing byte ranges. Keep the original common finite mask, 12-row
sidebands, two-row guards, C0/C1 conventions, r<=25 apertures, 30<r<=40 annuli,
column projection and r>35 smearing regression. Use native summed duration,
including the two-row negative. Run all nine inherited image tests plus
known-answer two-row controls for signed sums, guards and brightness
preservation in both conventions before pixels. No scientific math changes.

Retain gate order: CORRECTION_LINKED (|DELTA/COR| or |column DELTA/COR|>=0.5
in both conventions, complete apertures and matching original sign), then
SPATIALLY_STRUCTURED (displacement explained energy>=0.8 and advantage>=0.2
over brightness in both), otherwise UNRESOLVED_WITHIN_FIXED_SCOPE.
Unavailable fits remain unavailable. Keep independent long-double/scalar
audit tolerances: relative 2e-8, native absolute 1e-6, dimensionless 1e-8.

Inspect every representative's common-scale CAL/COR/DELTA figure. Stop after
the 14 fixed representatives. If all close, close this GJ 581 pair and prepare
rank-16 EC14599-2047 under separate header/table freezes. If any remain
unresolved, state the limitation before at most one separately frozen study
using retained data only. No extra pixels or visits to force closure; the
other five eligible GJ 581 visits remain outside this pair.

These diagnostic labels identify neither a unique cause nor artificial
origin. No detector, candidate, significance, sensitivity or coverage is
qualified. Closed WASP-103, HD 106315's three unresolved labels and bounded
study, prior targets and reserved TESS/M43 panels remain unchanged.
Calibration NOT_READY; request UNSENT. Publication is already authorized;
delegation remains deferred.
