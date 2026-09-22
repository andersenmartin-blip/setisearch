# LS8AJ — exact EC13080-1508 image payload and unchanged diagnostic

22 September 2026. **FROZEN BEFORE IMAGE OR SMEARING VALUES**.
Metadata freeze: `260a5b2ed88bc94102d8f679110f8be1272a8f05`.
Metadata result: `0bdaaf90f64a091999c2fee42e5ff7fbde388fb2`.
Audited L2 source: `b8724b092cf8f6a348b9f652b65cde080df21622`.

The independent metadata audit passes **58 unique exposure joins and
269 exact checks**, with zero image bytes. All 57
metadata-manifest entries and the future-image config were locally byte-verified.
This diagnostic includes the complete signed representative set:
**TG005201_N0**, negative, L2 row 65, one 60-second exposure,
original score -13.17039181262956. The second selected visit and both
positive cluster sets are empty. The score is not Gaussian sigma.

## Exact source identities and byte intervals

Use only CH_PR100002_TG005201_V0300 CAL/COR products. Exact filenames, ETags,
total sizes and metadata identities are retained in config/ls8aj_images.json.
Both image arrays are unscaled big-endian float64, 200x200 native
ADU, 320,000 bytes per frame. Both products have 93
frames, image start 17280 and offsets
(157, 759). NEXP=1 and EXPTIME=TEXPTIME=60 seconds,
PIPE_VER=14.1.2 agree with L2 separately for each product.

| Product | First byte | Count | Last byte inclusive |
|---|---:|---:|---:|
| SCI_CAL_SubArray | 16337280 | 9280000 | 25617279 |
| SCI_COR_SubArray | 16337280 | 9280000 | 25617279 |
| SMEAR | 29921280 | 46400 | 29967679 |

The original L2 context is 51:80. Native image indices and contiguous
intervals were determined by unique exposure joins, not assumed. Acquire
exactly **18,560,000 paired-image bytes plus 46,400 smearing bytes**.
Pin config, representatives, metadata/L2 manifests, metadata audit, unchanged
mathematical source, independent audit and tests in config/ls8aj_payload_scope.json.
Verify all pins, public freeze HEAD and clean tracked tree before acquisition.

Require HTTP 206, exact range/length/total, ETag and filename. Keep the
unchanged image fetch: at most three identical-range attempts for transport
failures, 90-second timeout, immediate stop on identity/contract assertions.
Save successful receipts, raw/compressed hashes and partial failures.
URL resolution retains at most three 45-second attempts, five-second spacing
and timeout-only retries. No alternate endpoint, product, aperture, frame,
visit or raw imagette is authorized. Verified retained ranges may be reused
offline; completed diagnostics must not be overwritten.

## Unchanged image calculation and gate order

Use hash-pinned cheops_image_pair.py unchanged. Fit median-centered local
linear pixel baselines to the original 12-row sidebands, with two guards
on each side. The event is local row 14 in the 29-row context. The common
finite CAL/COR mask uses event and sideband rows, excluding guards. Retain
CAL, COR and DELTA=COR-CAL temporal maps, analogous smearing maps, common-mask
column projections and the original r>35 smearing regression.

C0 uses the saved sideband mean centroid minus verified detector offsets;
C1 subtracts one from each coordinate. Keep r<=25 apertures, 30<r<=40
annuli and unweighted brightness+constant, displacement-gradients+constant
and combined fits. No recentering, extra masking, weighting or retuning.

Both conventions require complete apertures, valid COR denominators and
COR sign agreement with the original negative event. Apply the existing order:

1. **CORRECTION_LINKED** if both conventions have |DELTA/COR| or
   |column-DELTA/COR| >=0.5.
2. Otherwise **SPATIALLY_STRUCTURED** if both have available fits with
   displacement explained energy >=0.8 and an advantage >=0.2 over brightness.
3. Otherwise **UNRESOLVED_WITHIN_FIXED_SCOPE**. Unavailable fits stay unavailable.

These labels describe delivered processing or morphology, not a unique
physical cause, astrophysical origin or artificial emission. No new
screening cut or correction is adopted.

## Verification and stopping

All nine inherited synthetic image tests must pass in the full workflow
before pixels. Reuse known-answer controls for signs, durations, guards and
brightness preservation. No new scientific function is introduced here.
The independent event-map, regression, column-projection and rebuild functions
are AST-identical to LS8AG/LS8T. Independently decode retained bytes, check raw
and compressed hashes, ranges and metadata joins; reconstruct temporal maps
with long-double equations and spatial fits with scalar normal equations.
Keep relative 2e-8, native absolute 1e-6 and dimensionless absolute 1e-8
tolerances, exact masks/membership/counts/labels. Preserve audit failures.

Publish all retained inputs, receipts, maps, diagnostics, independent audit,
reference, environment, logs and checksums. The CAL/COR/DELTA figure uses one
common signed native-unit scale and both aperture outlines; inspect it
visually before interpretation. Stop after this representative. If it closes,
close EC13080-1508 and prepare rank-12 PG 1343-102 with separate header/table
freezes. If unresolved, state the remaining limitation before one separately
frozen retained-data study. No further pixels or visits to force closure.
The third eligible EC13080-1508 visit TG005203 stays outside scope.
Prior unresolved events and closed studies remain unchanged. Reserved TESS/M43
panels stay closed. Calibration is NOT_READY, its request unsent, publication
already authorized; delegation remains deferred.
