# LS8R — exact HD 136352 paired-image payload and fixed diagnostic

Status: **FROZEN BEFORE ANY LS8R IMAGE OR SMEARING VALUES**.
Metadata freeze: `7b4a39375dd4050dd24f005009ce7eb19498b01e`.
Metadata result: `223e5fbe65e949d3caffe98372f93e27e494085e`, PASS after
**176 unique CAL/COR joins and 812 exact checks**, with zero image bytes read.
L2 source: `69108d1939f5a1ed6a466d46f7376ed0f90dc2fb`, independently audited.

All three signed representatives are retained. Two have one event stack and
one has two. Each delivered stack combines NEXP=26 exposures; its TEXPTIME
is 44.2000007629395 s, not the individual EXPTIME of about 1.7 s.

## Immutable identities and byte ranges

The complete source identities, ETags, exact filenames, metadata checksums,
native frame indices and offsets are in `config/ls8r_images.json`. Its SHA-256,
the complete metadata and L2 manifests, metadata audit, representative list,
image mathematics and independent auditor are pinned in
`config/ls8r_payload_scope.json`. Verify all pins, freeze HEAD and clean tracked
tree before acquisition. No file or completed result is overwritten.

All image products are unscaled big-endian float64, 200x200 pixels, native ADU;
X_WINOFF=564 and Y_WINOFF=196. Each frame is 320,000 bytes. CAL/COR image data
start at byte 17,280; visits have 558 and 567 frames. The native image/L2
indices below coincide only after the independent timestamp/counter joins.

| Representative | Event rows | Context rows [start,stop) | CAL start / count | COR start / count | SMEAR start / count |
|---|---|---|---|---|---|
| TG000901_N0 | 46 | 32:61 | 10257280 / 9280000 | 10257280 / 9280000 | 178830080 / 46400 |
| TG000901_N1 | 196 | 182:211 | 58257280 / 9280000 | 58257280 / 9280000 | 179070080 / 46400 |
| TG000101_N0 | 432,433 | 418:448 | 133777280 / 9600000 | 133777280 / 9600000 | 182333440 / 48000 |

Acquire exactly **56,320,000 paired-image bytes plus 140,800 smearing bytes**.
Each smearing row is 200 float64 values. Use HTTP 206 with exact Content-Range,
Content-Length, total size, ETag and Content-Disposition. Only identical-range
transport retries, at most three total attempts, are allowed. Identity or
contract assertions stop immediately; never retry them away. Save gzip/raw
hashes, successful receipts, transport failures and partial acquired ranges.
No extra image frame, aperture, visit or raw imagette is authorized.

## Unchanged numerical diagnostic and gates

Use the pinned `cheops_image_pair.py` unchanged. The CAL/COR common finite
mask uses all sideband and event rows; guards do not define the mask or fit.
Fit a median-centered local linear baseline per pixel on 12 rows each side,
with two guards each side. Sum the original d=1 or d=2 event prediction
residuals to form CAL and COR maps; DELTA=COR-CAL. Use the analogous smearing
map, common-mask column projections and the original r>35 smearing regression.

Use the original sideband-centroid mean minus detector offsets as C0, and
C0 minus one in x/y as C1. Keep both, with r<=25 aperture and 30<r<=40
background annulus. Use unweighted brightness+constant, first-order x/y
gradients+constant and combined fits. Retain all diagnostic outputs.

Both conventions require complete apertures, valid COR denominator and
matching COR/L2 signs. Classify in this order:

1. **CORRECTION_LINKED** if each convention has either absolute DELTA/COR
   or absolute column-DELTA/COR >=0.5.
2. Otherwise **SPATIALLY_STRUCTURED** if each convention has available fits,
   displacement explained energy >=0.8 and advantage over brightness >=0.2.
3. Otherwise **UNRESOLVED_WITHIN_FIXED_SCOPE**, retaining unavailable fits.

No threshold, convention, aperture, pixel or representative is selected from
the images. No LS8P covariance weights or hypothetical subtraction is used.
A correction label denotes coupling to delivered processing; a spatial label
denotes morphology. Neither proves a unique physical cause or rules out source
variability. An unresolved label is not evidence for a SETI signal.

## Verification, reporting and stopping

Before pixel access, run seven inherited image known-answer tests plus two
new tests covering one/two-stack sums, guards and preservation of pure
brightness in both signs at this cadence. The two new tests pass locally.
The inherited suite requires its full repository reference module, absent
from the partial local source snapshot, and is required to pass in the complete
workflow checkout before any image values. This is an environment prerequisite,
not a numerical method or tolerance change.

The LS8R independent event-map, regression, column-projection and rebuild
functions are AST-identical to LS8O. Independently decode raw floats, recheck
metadata joins/receipts, reconstruct maps with long-double temporal equations,
and spatial fits with scalar normal equations. Keep original numeric
tolerances: relative 2e-8, native absolute 1e-6, dimensionless absolute 1e-8;
all masks, memberships, counts and labels are exact. A disagreement stops
scientific promotion with a preserved failure, not a loosened tolerance.

Publish all three CAL/COR/DELTA maps with one common symmetric full-frame
scale per representative, both original apertures, complete raw ranges,
diagnostics, independent reference/audit, logs, environment and checksum
manifest. Visually inspect all figures before the interpretive status update.

If every event closes under the fixed gates, close this pair and prepare the
independent rank-4 TESS_260647166 transfer under new metadata/science freezes.
If any remain unresolved, first state the concrete limitation before one
separately frozen retained-data follow-up. Stop this image stage after all
three regardless of outcome; do not widen or rerun to obtain closure.
No qualified candidate, detector or coverage is claimed. All earlier failures,
closed GJ 1132/WASP-189 outcomes, reserved TESS/M43 data and the unsent
raw-imagette calibration request remain preserved.
