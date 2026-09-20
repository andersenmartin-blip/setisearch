# Continue after LS8P

The single retained-data study required by LS8O is **complete and closed**.
Verified result commit: **`65c2f1a0c1da8a7a63c9ace8ca9f06af4c9b491a`**,
directory `results_ls8p_verified`. The initial serialization failure remains
visible in `results_ls8p_residuals`; it is superseded by the verified audit,
not erased or relabeled as a successful initial run.

## Scientific outcome

All five GJ 1132 negative controls retain **UNRESOLVED_WITHIN_FIXED_SCOPE**.
LS8N's **zero positive crossings in 699 eligible overlapping windows** is
unchanged. No selected event is promoted to a SETI candidate. The bounded
follow-up now quantifies the local-variability and coordinate limitations;
it does not identify a unique stellar or instrumental cause.

The table uses COR, the combined weighted brightness/gradient/constant
model and the frozen three-exposure temporal covariance model. The ratios
compare remaining event-map energy with propagated training residual energy.

| Control | Residual/reference C0 / C1 | Held three-row blocks >= native C0 / C1 | Correlated/IID variance C0 / C1 |
|---|---:|---:|---:|
| TG000401_N0 | 2.017149 / 2.010914 | 6/8 / 6/8 | 1.666138 / 1.655448 |
| TG000403_N0 | 1.494935 / 1.429729 | 8/8 / 8/8 | 1.492090 / 1.473705 |
| TG000403_N1 | 1.867250 / 1.755100 | 8/8 / 8/8 | 1.385164 / 1.365939 |
| TG000403_N2 | 1.625038 / 1.520501 | 8/8 / 8/8 | 1.474783 / 1.456331 |
| TG000403_N3 | 1.736429 / 1.631934 | 8/8 / 8/8 | 1.454245 / 1.434975 |

The frozen correlation model raises COR event-variance estimates by about
**37–67%** relative to the IID model. COR residual/reference ratios are
**1.43–2.02**, versus **2.11–3.36** for IID propagation. Most of the fixed
held comparisons have at least as large a residual/reference ratio.
This does not establish an ordinary-noise origin or a false-alarm probability:
the eight targets share training rows, have different leverage and profile
estimates, and were not selected by the same threshold as the native events.
The pooled short-lag covariance is descriptive, not a calibrated noise law.

The new weighted displacement fit for the original near-80% case,
TG000403_N1, explains **48.4860% / 50.6688%**. These are new descriptive
weights and do not replace LS8O's original **79.74861% / 83.79823%** or its
requirement of at least 80% in both conventions. The original label stays
unchanged; choosing weights or a convention to force a pass is not allowed.

## Coordinate sensitivity is accounted for at the boundary

TG000403_N2 has 1,892 pixels in the aperture intersection and 71 exclusive
pixels in each convention. The exact signed contribution of those boundary
sets explains why the original DELTA aperture sum changes sign:

| Region | CAL sum ADU | COR sum ADU | DELTA sum ADU |
|---|---:|---:|---:|
| C0/C1 intersection | -50,291.832725 | -49,130.306410 | +1,161.526315 |
| C0-only, 71 pixels | +22,696.290720 | +5,169.668733 | -17,526.621987 |
| C1-only, 71 pixels | +3,363.758151 | +3,657.931862 | +294.173710 |
| Entire C0 | -27,595.542005 | -43,960.637677 | -16,365.095672 |
| Entire C1 | -46,928.074573 | -45,472.374548 | +1,455.700026 |

The DELTA difference is **+17,820.795698 ADU**, exactly the C1-only minus
C0-only contribution within floating-point tolerance. Thus the original
DELTA/COR ratios, +0.372267 and -0.032013, depend strongly on a correction
contribution in the C0-only boundary. This is numerical localization, not
proof of the physical cause or permission to remove those pixels.

The same boundary identities, signed pixel lists and energy budgets are
retained for all five cases. Native apertures and both conventions are kept.
Model changes are not reduced to a boundary-only explanation because their
sideband background/profile definitions also change with convention.

For this same case, CAL's weighted combined residual/reference ratio is
2.945868 in C0 and 1.496945 in C1, with 54.2043% and 19.4637% of weighted
residual energy in the ten largest pixels. COR is less sensitive. Paired
residual accounting keeps the large negative CAL/DELTA cross term instead
of treating correction and pre-correction energies as separate cause fractions.

## Signal protection and closure

All 120 signed pure-template controls recover the known three-row brightness
or gradient coefficients. All 200 signed compact controls and 320 additive
checks are retained. A hypothetical displacement-plus-constant subtraction
would remove about **24–38% of injected brightness flux** across the CAL/COR
and C0/C1 cases. No such subtraction or veto is adopted. Pure first-order
templates and compact injections do not establish performance for all real
signals or nuisance patterns.

Seventeen tests preceded native analysis. A later serialization regression
test reproduces the exact failure and verifies its representation-only repair.
The final independent audit passes **1,400,704 numerical comparisons and
1,529,059 exact checks**, with zero disagreements. It verifies all 20 native
product/convention cases, 160 held-block cases, 320 signed controls, saved
arrays, boundary lists, per-context duplicates and original maps. These
comparison counts are reproducibility checks, not independent observations.

All five residual figures have been visually inspected and their downloaded
files match the immutable manifest. They retain both conventions, full fixed
apertures and all held blocks. The maps show spatially structured residuals;
visual appearance does not set a new classification or establish their origin.

**The GJ 1132 bounded follow-up ends here.** Do not retune its apertures,
backgrounds, lag lengths, spatial templates or thresholds, or acquire extra
GJ 1132 pixels/visits for this closed study. Preserve every original outcome.

## Next action: independent rank-3 HD 136352 transfer

Use the unchanged LS8J chronological cohort ledger and reconciliation; do not
repeat the population census or reorder hosts based on these results.

| Pair order | File key | Existing start MJD |
|---|---|---:|
| 1 | CH_PR100041_TG000901_V0300 | 58943.6307305439 |
| 2 | CH_PR100041_TG000101_V0300 | 58953.6827227982 |

The ledger's exposure metadata is NEXP=26, EXPTIME approximately 1.7 seconds,
TEXPTIME approximately 44.2 seconds. These native science values remain
**unopened** at this checkpoint. Exact metadata must be verified independently
before deriving any table byte ranges; do not copy GJ 1132's 60-second scope.

1. Freeze this exact pair and a bounded metadata/header-only examination,
   preserving all request receipts, source identities, headers, schema and
   exposure checks. Reuse the metadata-before-science pattern from LS8N.
   Stop explicitly on incompatibility rather than substituting another host.
2. After compatible headers, separately freeze the exact two DEFAULT-L2
   byte ranges. Transfer the unchanged hash-pinned stable LS8K/LS8N screen
   and independent auditor: one/two/three-row windows, original eligibility,
   sidebands, guards, score thresholds and signed cluster representation.
   Apply neither LS8P noise weights nor a new residual veto to that screen.
3. Publish all signed outcomes, eligible denominators and independent audit.
   If image follow-up is indicated, freeze metadata joins before exact image
   ranges and retain every eligible signed representative. No later data are
   authorized implicitly by a previous byte scope.

This is the next independent transfer, not an already completed experiment
or a promise of a detection. No qualified detector, candidate or additional
qualified observing coverage is claimed. Closed WASP-189 data, raw imagettes,
reserved TESS sectors and M43 held-out panels remain unchanged. The separate
raw-imagette calibration gate is NOT_READY and its request is still unsent.
Standing research and publication authorization continues without another
per-stage permission request; collaboration remains deferred.

[All LS8P outcomes and figures](results_ls8p_verified/REPORT.md) ·
[Scientific freeze](LS8P_THREE_SUM_PROTOCOL.md) ·
[Preserved serialization failure and repair](LS8P_AUDIT_RECOVERY.md) ·
[Publication identities](PUBLICATION_2026-09-20_LS8P.md).
