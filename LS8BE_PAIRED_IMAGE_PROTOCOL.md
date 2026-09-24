# LS8BE — exact paired-image diagnostic for the GJ 494 signed event

24 September 2026. **FROZEN BEFORE IMAGE AND SMEARING PAYLOAD ACCESS**.
L2 result: `a5a3fd0e1678c2e77d505d9fac209e1cba55f9a9`.
Metadata freeze: `5fcf8e4e89cc06b68493203fb25eba03e2dc6fad`.
Metadata result: `0bfee749d24f5a65f8bb93e014ad6b578e3bb851`.

Metadata and the independent joins pass: **269 exact checks**, 58 unique
CAL/COR exposure matches, zero pixels read. The complete signed set has one
positive representative, with 29 distinct context exposures. The second
original visit has 48 eligible windows and no crossings; it has no selected
image follow-up. Two later GJ 494 visits remain outside the pair.

## Exact payload

The context is in CH_PR100018_TG007401_V0300. CAL and COR each have 83 frames,
unscaled 200x200 float64 ADU images, 320,000 bytes per frame, detector offsets
(157,759) and first image data byte 17,280. NEXP=1, EXPTIME=TEXPTIME=42 seconds
and pipeline 14.1.2 match its own L2 header. Exact ETags, filenames, total
sizes and layouts are retained in config/ls8be_images.json. Exposure joins
were checked rather than inferred from row-index equality.

| Context | Event row | Context [start,stop) | CAL/COR start, each | Bytes per CAL/COR range | Smearing start | Smearing bytes |
|---|---:|---|---:|---:|---:|---:|
| TG007401_P0 | 53 | 39:68 | 12497280 | 9280000 | 26699520 | 46400 |

Acquire exactly **18,560,000 CAL/COR bytes and 46,400 smearing bytes** in three
fixed ranges. There are no overlapping representative contexts or repeated
source exposures within this scope. No other pixels, apertures, raw imagettes
or visits are authorized.

Require public freeze HEAD, clean tracked checkout, all 33 input pins and
the complete metadata manifest before access. Require HTTP 206, exact
range/length/total, matching If-Match ETag and exact filename. Preserve raw
and compressed SHA256, receipts, attempts, identities and partial failures.
Reuse unchanged acquisition: at most three identical range attempts for
OSError/TimeoutError, never retry identity/contract assertions. URL resolution
uses its separate unchanged timeout-only bound.

## Unchanged diagnostic and audit

Run all 11 inherited image tests before pixels. Use the unchanged hash-pinned
image core and prospectively frozen independent auditor. Its event_map,
regression, columns_projection and rebuild functions are AST-identical to
LS8BB. Native event sums use retained BJD times, the original 12-row
sidebands and two guards per side. The common finite mask uses sideband/event
pixels. Source centers use only saved sideband centroids, with C0/C1
conventions, radius-25 apertures, 30<r<=40 annuli, column projection and r>35
smearing regression. Unavailable fits remain unavailable. No masks, centers,
templates, thresholds or subtraction are selected from the outcome.

Gate order remains fixed, requiring complete apertures and COR/L2 sign
agreement in both conventions. First, CORRECTION_LINKED if absolute
DELTA/COR or column-DELTA/COR >=0.5 in both. Otherwise SPATIALLY_STRUCTURED
requires displacement explained >=0.8 and its advantage over brightness
>=0.2 in both. Otherwise UNRESOLVED_WITHIN_FIXED_SCOPE. Labels do not
establish a unique physical cause, artificial origin or source variability.

Independent struct decoding, long-double temporal equations and scalar
spatial equations reconstruct the complete context, maps, fits and label.
Keep exact checks and relative 2e-8, native absolute 1e-6 and dimensionless
absolute 1e-8 tolerances. Preserve any failure and stop promotion without
relaxing tolerances or rerunning native science to seek a pass. Publish and
visually inspect the common-scale CAL/COR/DELTA figure. Only its presentation
layout is widened relative to LS8BB; numerical maps and scales are unchanged.

## Preservation and stopping

Publish all raw ranges, maps, diagnostics, independent audit, report, figure,
logs, environment, freeze identity and checksums on the scientific branch.
Retain the sparse checkout and successful-checkout preservation guard. An
optional seven-day Actions artifact contains only the same retained results,
using upload-artifact v4 at compression level 0. It is a transport copy;
Git is the durable publication. Artifact failure never repeats native
analysis or relaxes the scientific success gate. Verify any downloaded copy.

If the event receives a descriptive closure label, close this pair and
prepare **LS8BF, rank-24 2MASS J11474440+0048164**, chronological pair
CH_PR100018_TG007101_V0300 / CH_PR100018_TG007102_V0300, under separate header
and L2 freezes. If unresolved, state the specific limitation before at most
one separately frozen study of the complete unresolved set using retained
data only. Do not widen acquisition to force closure.

No candidate, detector, probability, sensitivity or qualified observing
coverage is claimed. Original L2 rules, earlier labels, unassessed points,
closed studies and reserved TESS/M43 panels remain unchanged. Calibration
NOT_READY; request UNSENT. Publication authorized; delegation deferred.
