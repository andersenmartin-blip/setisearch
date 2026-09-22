# LS8AM — exact HD 106315 image payload and unchanged diagnostic

22 September 2026. **FROZEN BEFORE IMAGE OR SMEARING VALUES**.
Metadata freeze: a6fc2353a4e9bd4dd81bc919b219c2f99a84d507.
Metadata result: b62a0c945c47ad40a0fcc42b21ad6c1f2ca8f3d8.
Audited L2 source: 36d081fac65ca35bccbfde5220660fd547d44bc9.

The independent metadata audit passes **174 unique exposure joins and
803 exact checks**, with zero image bytes. All 104
metadata-manifest entries and the future-image config were locally byte-verified.
This diagnostic includes the complete signed representative set:

| Representative | Sign | L2 event row | Original context [start,stop) | Duration | Original score |
|---|---|---:|---|---|---:|
| TG000801_P0 | positive | 223 | 209:238 | 1 row / 41 s | +44.503884094991555 |
| TG000801_P1 | positive | 363 | 349:378 | 1 row / 41 s | +9.691535552281110 |
| TG001401_P0 | positive | 178 | 164:193 | 1 row / 41 s | +28.143188663326402 |

Both negative cluster sets are empty. Scores are not Gaussian sigma.

## Exact source identities and byte intervals

Use only CH_PR100041_TG000801_V0300 and CH_PR100041_TG001401_V0300 CAL/COR
products. Exact filenames, ETags, total sizes and metadata identities are
retained in config/ls8am_images.json. All four image arrays are unscaled
big-endian float64, 200x200 native ADU, 320,000 bytes per frame.
NEXP=1 and EXPTIME=TEXPTIME=41 seconds, PIPE_VER=14.1.2 agree with L2
separately for every product.

| Exact visit | Product | Frames | Image first byte | Detector offsets | Native unit |
|---|---|---:|---:|---|---|
| CH_PR100041_TG000801_V0300 | SCI_CAL_SubArray | 872 | 17280 | (564, 196) | ADU |
| CH_PR100041_TG000801_V0300 | SCI_COR_SubArray | 872 | 17280 | (564, 196) | ADU |
| CH_PR100041_TG001401_V0300 | SCI_CAL_SubArray | 1510 | 17280 | (157, 759) | ADU |
| CH_PR100041_TG001401_V0300 | SCI_COR_SubArray | 1510 | 17280 | (157, 759) | ADU |

| Representative | Product | First byte | Count | Last byte inclusive |
|---|---|---:|---:|---:|
| TG000801_P0 | SCI_CAL_SubArray | 66897280 | 9280000 | 76177279 |
| TG000801_P0 | SCI_COR_SubArray | 66897280 | 9280000 | 76177279 |
| TG000801_P0 | SMEAR | 279688640 | 46400 | 279735039 |
| TG000801_P1 | SCI_CAL_SubArray | 111697280 | 9280000 | 120977279 |
| TG000801_P1 | SCI_COR_SubArray | 111697280 | 9280000 | 120977279 |
| TG000801_P1 | SMEAR | 279912640 | 46400 | 279959039 |
| TG001401_P0 | SCI_CAL_SubArray | 52497280 | 9280000 | 61777279 |
| TG001401_P0 | SCI_COR_SubArray | 52497280 | 9280000 | 61777279 |
| TG001401_P0 | SMEAR | 483969920 | 46400 | 484016319 |

Native image indices and contiguous intervals were determined by unique
exposure joins, not assumed. The original contexts are disjoint within each
visit. Acquire exactly **55,680,000 paired-image bytes plus 139,200 smearing
bytes**. Pin config, representatives, metadata/L2 manifests, metadata audit,
unchanged mathematical source, independent audit and tests in
config/ls8am_payload_scope.json. Verify all pins, public freeze HEAD and clean
tracked tree before acquisition.

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
on each side. Each event is local row 14 in its 29-row context. The common
finite CAL/COR mask uses event and sideband rows, excluding guards. Retain
CAL, COR and DELTA=COR-CAL temporal maps, analogous smearing maps, common-mask
column projections and the original r>35 smearing regression.

C0 uses the saved sideband mean centroid minus verified detector offsets;
C1 subtracts one from each coordinate. Keep r<=25 apertures, 30<r<=40
annuli and unweighted brightness+constant, displacement-gradients+constant
and combined fits. No recentering, extra masking, weighting or retuning.

Both conventions require complete apertures, valid COR denominators and
COR sign agreement with each original positive event. Apply the existing order:

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
are AST-identical to LS8AJ/LS8T. Independently decode retained bytes, check raw
and compressed hashes, ranges and metadata joins; reconstruct temporal maps
with long-double equations and spatial fits with scalar normal equations.
Keep relative 2e-8, native absolute 1e-6 and dimensionless absolute 1e-8
tolerances, exact masks/membership/counts/labels. Preserve audit failures.

Publish all retained inputs, receipts, maps, diagnostics, independent audit,
reference, environment, logs and checksums. Each CAL/COR/DELTA figure uses one
common signed native-unit scale and both aperture outlines; inspect every
figure visually before interpretation. Stop after all three representatives.
If all close, close HD 106315 and prepare rank-14 WASP-103 with separate
header/table freezes. For any unresolved event, state the remaining limitation
before one separately frozen retained-data study. No further pixels or visits
to force closure. HD 106315 has only these two eligible visits in the ledger.
Prior unresolved events and closed studies remain unchanged. Reserved TESS/M43
panels stay closed. Calibration is NOT_READY, its request unsent, publication
already authorized; delegation remains deferred.
