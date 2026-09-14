# LS7J: motion and outside-aperture information

Prospective specification, 14 September 2026. Parent: `9647667a92f0bd6aed37cd71f0510c14f7b77fe6`.
The owner asked to continue the plan after LS7I's completed negative result.
This is the proposed auxiliary-information feasibility study, executed as one
implementation, evaluation, audit and publication package. LS7I remains closed.
Publish this protocol, configuration, code, tests and audit before evaluation.

## Question and boundary

Can a fixed physical scene-motion prediction plus a simultaneous plane inferred
from outside-aperture pixels improve the native background while preserving a
stellar pulse, including wings outside the aperture? Test both closed sectors.
No new ridge, learned motion gain, margin sweep, nuisance-bank extension, event
selection, covariance calibration or detector decisions enter this study.

This is a necessary-information test, not a replacement for the joint detector
qualification in the original plan. The historical pointing controls change
pixels without updating mission motion metadata. Their digital responses can be
measured, but cannot establish rejection of physically consistent motion events.
Most historical stellar patterns have zero outside-aperture flux; their exact
preservation alone cannot establish protection of real stellar wings.

## Fixed inputs and field verification

Reuse the twenty sealed 401-cadence, 11×11 contexts indexed by
`results_ls7i_inputs/datasets.json`, ten each from TESS sectors 29 and 32 of
TIC 307210830. Their original 21- and 18-pixel apertures leave 100 and 103
outside pixels. Structural inspection before this freeze found every native
outside-pixel value finite. No new prediction or response outcome was inspected.

Restore only the two original light-curve products named and hashed in
`config/ls7j_auxiliary.json`. Verify byte counts, SHA-256, target, sector,
20-second cadence, TDB/BJD reference, original aperture, cadence identities,
times within 1e-7 day and compatibility with the original combined quality mask.
Extract all 8,020 selected rows without changing eligibility or interpolating.
Independently locate those rows by unique cadence number in the raw files.
The existing input audits remain the basis for pixel calibration and extraction.

| Fields | Role in LS7J |
|---|---|
| POS_CORR2, POS_CORR1 | Motion predictor, explicitly in row/column (YX) order |
| MOM_CENTR2/1 and errors | Inventory of target-flux centroids; excluded from prediction |
| PSF_CENTR2/1 and errors | Inventory only; missing values retained |
| SAP_BKG and SAP_BKG_ERR | Inventory only |

The [TESS data-products specification, Rev F, Tables 8 and 13](https://archive.stsci.edu/files/live/sites/mast/files/home/missions-and-data/active-missions/tess/_documents/EXP-TESS-ARC-ICD-TM-0014-Rev-F.pdf)
defines POS_CORR as local CCD motion corrections in pixels and distinguishes
them from flux-weighted and PSF-fitted target centroids. Its field definitions
do not establish upstream independence from a variable target. LS7J records
column presence, units, formats, finite counts and processing metadata. It never
calls a target centroid an independent attitude measurement. A separate, simple
aperture-moment example measures pulse-induced centroid changes; it is not a
reimplementation of the mission centroid algorithm.

If any POS_CORR coordinate required for a window is nonfinite, motion and
combined predictions are unavailable. Preserve the row and denominator. Plane
alone remains a predeclared ablation. No zero-filling, sign selection or fallback
substitution into the primary method is allowed.

## One physical correction and its ablations

For event interval [lo, hi), use the same protected long sidebands as LS7I:
[lo−60, lo−5) and [hi+5, hi+60), 55 samples each. Reference image is their
pixelwise median. Local aperture scale is 1.482602218505602 times the MAD of
the 108 within-sideband first differences of aperture-summed flux, divided by
sqrt(2). The event and five-cadence guards do not enter this reference or scale.

1. **Motion.** Subtract the sideband-median POS_CORR vector from its event mean.
   Shift the reference by this YX displacement with unit gain, bilinear
   interpolation and nearest boundaries, preserving the full-stamp flux by
   rescaling. Predicted change is shifted minus reference. Use the existing
   `pointing_delta` convention; do not estimate a gain from evaluated data.
2. **Outside plane.** Use full-stamp basis [1, (y−5)/5, (x−5)/5]. Weight each
   outside pixel by its sideband-difference MAD scale. Floor variance at 1e-6
   times the median strictly positive outside variance; record floored counts.
   No pixel clipping or data-driven spatial selection is allowed.
3. **Source protection.** Build nine full-stamp scene proxies from the observable
   reference: subtract the median of its forty border pixels, clip negatives to
   zero, bilinearly shift with zero boundaries, then normalize the aperture sum
   to one. Use exactly the nine quarter-pixel displacements in the configuration.
   Retain wings. These empirical scene proxies may include neighbors and are
   not a calibrated target PRF. Whiten their outside values, keep SVD directions
   above 1e-10 of the largest singular value, and project the weighted plane
   orthogonally to that source subspace.
4. Require projected-plane rank three under the same tolerance and condition
   number at most 1e8. Otherwise plane and combined are unavailable. Its
   pseudoinverse divided by outside noise maps simultaneous outside-pixel
   changes to plane coefficients. No event-aperture value enters that fit.
5. **Primary combined:** subtract motion from the observed difference, fit its
   outside plane, and add that plane to the motion prediction. Subtract this
   combined prediction from the aperture difference. **Plane alone** fits the
   original outside difference; **motion alone** and **static** are the other
   ablations. There is no post-result selection of a winning ablation.

All numerical constants above are fixed even when repeated literally in the
independent audit. Finite-context validation may inspect the whole cube, but
inference profiles and weights use only the protected sidebands.

## Native diagnostic

Reuse the 420 LS7I windows in their original order: starts 90, 130, 170, 210,
250, 290 and 330; widths 2, 3 and 5; all twenty backgrounds. Use the sixty
original static mean/covariance pairs for the same sector, width and excluded
background. These were built from the other nine backgrounds; verify their
identity and training exclusions rather than fitting a new covariance.

Apply each correction before subtracting the common static mean, normalize by
the local aperture scale, whiten with the common static covariance, project out
the free uniform component and sum squared residuals. Reproduce each original
static energy. The measured ratios include correction noise on these native
windows. They do not supply a calibrated detector error model or false-alarm
probability. Contexts and overlapping sidebands make windows dependent.

## Complete response ledger and wing supplement

Retain all 6,720 historical recipes and all 360 previously separate sector-32
shape controls, in their original order and cohorts. Keep temporal windows,
amplitudes, patterns and sparse residuals unchanged. Record the aperture
response to the whole addition and, separately, to the stellar pulse with the
same sparse residual held in both sides of a paired difference. Check every
addition is zero in the protected reference bands.

Add a separate **2,400-row full-stamp response supplement**. Parents are all 240
base nominal stellar cases with target scores 8.5, 12 or 20: two box durations
(30 and 100 seconds), two phases (0 and 10 seconds), ten anchors per sector.
For each parent, use two profile classes and five shifts: zero and the four
(±0.2, ±0.2)-pixel diagonals. The classes are the unblurred full-stamp scene
proxy and the same proxy broadened by a fixed sigma=0.5-pixel Gaussian with
truncate=4 and zero boundaries. Build injection profiles from the median of
the full native context; this is injection truth only and is never an inference
feature. Normalize aperture sum to one, retaining external wings. Reuse each
parent's scale and temporal window without score retuning. Store all 200
distinct patterns and explicit parent links; new rows have no historical source
ledger row. Total response ledger: **9,480**, with 600 rows per new class per
sector. These are response checks, not 9,480 detections or independent events.

For expected aperture pulse s and paired corrected response t, record gain
(s dot t)/(s dot s) and relative L2 distortion norm(t−s)/norm(s). Zero pulses
have no metric. Metadata are held fixed in digital injections; this tests the
downstream correction only, not upstream pulse preservation by SPOC processing.

## Fixed feasibility gates

Every requirement applies separately to each sector. All must pass on both.

| Requirement | Threshold |
|---|---|
| Primary native availability | All 210 windows |
| Primary/native total energy divided by static | At most 1 |
| Backgrounds with energy ratio below 1 | At least 6 of 10 |
| Worst background energy ratio | At most 2 |
| All operators and nine protected profiles per frame | Valid; distortion at most 1e-8 |
| Historical aperture-limited stellar responses | All 1,320 available; distortion at most 1e-10 |
| New unblurred full-stamp responses | All 600 available; distortion at most 0.01 |
| New broadened full-stamp responses | All 600 available; distortion at most 0.05 |
| Independent audit | Pass, including raw light-curve extraction |

Missing rows fail their availability requirements. Publish all failed response
IDs and subgroup counts. The distortion limits are engineering requirements,
not confidence levels or retrospectively selected tolerances.

## Audit, publication and decision

Nine synthetic tests cover guard protection, exact source/plane separation,
event-aperture exclusion, motion axes/gain, missing metadata, centroid response,
wing mismatch, and independent geometry/solver agreement. The real-data audit
reconstructs geometry with scalar bilinear interpolation and explicit Gaussian
kernels. It verifies every operator using simultaneous source-plus-plane least
squares on all outside unit inputs, rather than the evaluator's projected
pseudoinverse. Independently reconstruct all injected cubes, native energies,
response vectors, coefficients, missing-data denominators and gates. Reuse
earlier unchanged extraction/baseline audits by their recorded hashes.

Publish sources, extracts, operators, recipes, responses, all gates, a readable
figure, response-failure list, audit and runtime logs with output checksums.
Automatic publication occurs for an audited scientific failure as well as a
pass. An acquisition or implementation failure is reported explicitly; do not
change scientific constants as a repair.

If feasibility passes, prepare a separately specified joint detector study
with correction uncertainty, consistent pixel/motion controls and upstream
signal-dependence requirements. A feasibility pass does not open unused data.
If it fails, close this fixed correction route and identify the exact missing
information from its saved diagnostics. Do not append another plane, gain,
profile, cut or covariance search to this experiment. Preserve all earlier
results and M43 held-out panels. Update the operational status and main README
under the standing publication authorization.
