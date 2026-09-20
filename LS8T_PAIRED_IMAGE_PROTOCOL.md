# LS8T — exact TESS_260647166 paired-image payload and fixed diagnostic

Status: **FROZEN BEFORE ANY LS8T IMAGE OR SMEARING VALUES**.
Metadata freeze: `7ee634cc2eee9f811009acba4cc45ee789261e35`.
Metadata result: `6960be53f8e5ce008983a85876517b338013b177`, independent
**PASS after 120 unique joins and 556 exact checks**, with zero image bytes.
Audited L2 source: `cc05ba9a55a98bcfe6e1c747820ec4dd3265617f`.

Retain both signed representatives. TG000101_N0 sums three 42-second
exposures (126 seconds); TG015701_P0 uses one 49-second exposure. Each
visit has NEXP=1. Their original scores are -10.085104590 and +45.460348286;
these are not Gaussian significances.

## Immutable identities and byte intervals

Complete filenames, sizes, ETags, native frame indices, metadata hashes and
offsets are in `config/ls8t_images.json`. Pin that file, the representative
list, complete metadata/L2 manifests, metadata audit, original image
mathematics and independent auditor in `config/ls8t_payload_scope.json`.
Verify every pin, the executing freeze HEAD and clean tracked tree before
acquisition. Refuse to overwrite a completed diagnostic.

All image planes are unscaled big-endian float64, 200x200 native ADU,
320,000 bytes per frame. Data start at byte 17,280. TG000101 has 983 frames
and detector offsets (715,181); TG015701 has 764 frames and offsets (157,759).
The frame/L2 row indices below coincide only after unique exposure joins.

| Representative | Event rows | Context [start,stop) | CAL start / count | COR start / count | SMEAR start / count |
|---|---|---|---|---|---|
| TG000101_N0 | 317–319 | 303:334 | 96977280 / 9920000 | 96977280 / 9920000 | 315395520 / 49600 |
| TG015701_P0 | 217 | 203:232 | 64977280 / 9280000 | 64977280 / 9280000 | 245087360 / 46400 |

Acquire exactly **38,400,000 paired-image bytes plus 96,000 smearing bytes**.
Every smearing row is 200 float64 values. Require HTTP 206, exact range and
length, source total size, ETag and Content-Disposition. Permit only
identical-range transport retries, at most three total attempts. Identity
or contract assertions stop immediately without retry. Preserve successful
receipts, raw/compressed hashes, failed transport receipts and partial data.
No extra frame, aperture, visit or raw imagette is authorized.

## Unchanged diagnostic and gates

Use the pinned `cheops_image_pair.py` unchanged. The common finite CAL/COR
mask uses all sideband and event rows; guards do not enter the mask or fit.
Fit the median-centered local linear pixel baseline on 12 rows each side,
with two guards each side, and sum residuals over the original d=3 or d=1
event. Retain CAL, COR, DELTA=COR-CAL and analogous smearing maps, common-mask
column projections and the original r>35 smearing regression.

C0 is the sideband-centroid mean minus that visit's detector offsets; C1 is
C0 minus one in both coordinates. Keep both, with r<=25 source aperture
and 30<r<=40 background annulus. Fit unweighted brightness+constant,
first-order x/y gradients+constant and combined models. Keep every output.

Both conventions must have complete apertures, valid COR denominators and
COR signs matching that event's original signed L2 selection. In order:

1. **CORRECTION_LINKED** if each convention has either absolute DELTA/COR
   or absolute column-DELTA/COR >=0.5.
2. Otherwise **SPATIALLY_STRUCTURED** if each convention has available fits,
   displacement explained energy >=0.8 and advantage over brightness >=0.2.
3. Otherwise **UNRESOLVED_WITHIN_FIXED_SCOPE**, retaining unavailable fits.

No template, weight, convention, aperture, pixel, score or representative
is selected from these images. No previous covariance weighting or
hypothetical subtraction becomes a cut. The labels describe processing
coupling or spatial morphology; none determines one physical cause or
excludes source variability. An unresolved label is not a SETI detection.

## Verification, reporting and stopping

Before payload, require all seven inherited image tests plus two new
known-answer tests for one/three-row event sums, guard exclusion and
pure-brightness preservation in both signs at 49/42 seconds. The two new
tests pass locally; the full nine-test suite must pass in the workflow
checkout before values. No native input enters these synthetic tests.

The independent LS8T event-map, regression, column-projection and rebuild
functions are AST-identical to LS8R. Independently decode raw floats,
recheck metadata joins and receipts, and reconstruct temporal maps with
long-double equations and spatial fits with scalar normal equations.
Keep relative tolerance 2e-8, native absolute 1e-6 and dimensionless absolute
1e-8. Masks, memberships, counts and labels are exact. Preserve any failure
without weakening a tolerance or scientific gate.

Publish both CAL/COR/DELTA figures with one common symmetric full-frame
scale per event, both apertures, all raw ranges/receipts, diagnostics,
independent reference and audit, logs, environment and checksums. Visually
inspect both figures before the interpretive status update.

If both events close under the fixed gates, close this pair and prepare
rank-5 EC 12578-2107 under new metadata/science freezes. If either remains
unresolved, state the concrete limitation before a separately frozen
retained-data follow-up. Stop this image stage after both representatives;
do not widen acquisition or rerun to force closure. No qualified candidate,
detector or observing coverage is claimed. Closed studies, reserved TESS/M43
data, raw imagettes and the unsent calibration request remain unchanged.
