# LS8AN — retained HD 106315 residual and local-noise study

22 September 2026. **FROZEN_BEFORE_NEW_NATIVE_DERIVED_CALCULATION**.
Publish this protocol, configuration, producer, independent auditor, report
and workflow together before execution. The recorded Actions GITHUB_SHA is
the freeze identity; the producer requires that exact clean tracked checkout.

## Specific limitation and complete scope

LS8AL's 2,382 rows and 4,698 eligible overlapping windows have 13 positive
crossings in three clusters and zero negative crossings. The independent L2
audit passes 56,376 comparisons. Its complete signed representative set has
completed the separately frozen LS8AM image diagnostic and independent audit:
283,611 numerical comparisons and 481,739 exact checks pass without disagreement.
All nine inherited image tests pass. The L2 figure and all three CAL/COR/DELTA
figures were visually inspected. Thirty-four of 40 image-manifest entries were
additionally verified locally; the six compressed CAL/COR cubes retain their
exact public identities and were checksum-verified and independently decoded
by the image workflow. This retained-data workflow verifies the complete
manifest and every raw cube digest before use.

All three positives remain **UNRESOLVED_WITHIN_FIXED_SCOPE**. Every original
aperture is complete and the COR aperture sums retain the positive L2 sign.
The following fixed image diagnostics do not reach their respective gates:

| Representative | DELTA/COR C0 / C1 | Column DELTA/COR C0 / C1 | COR displacement explained C0 / C1 | COR brightness explained C0 / C1 |
|---|---:|---:|---:|---:|
| TG000801_P0 | -0.166952 / -0.153053 | -0.147398 / -0.153454 | 77.57754% / 77.58310% | 3.01835% / 2.98551% |
| TG000801_P1 | -0.051078 / -0.050873 | -0.107098 / -0.104893 | 60.38468% / 60.38728% | 5.08258% / 5.06973% |
| TG001401_P0 | +0.355280 / +0.365547 | +0.220986 / +0.219316 | 37.64951% / 37.59867% | 3.20429% / 3.20018% |

The first two figures show signed structure over the stellar profile in CAL
and COR. The third figure's full-frame color scale is dominated by a feature
outside the source aperture, while the aperture's COR sums remain positive.
These visual descriptions do not assign causes or replace the original 80%
displacement gate. Smearing regressions remain rank deficient and unavailable.

The remaining question is the size and spatial distribution of the residual
relative to local variability, including exact C0/C1 boundary contributions.
The current fits establish neither a unique cause nor a calibrated significance.
No new shape model, mask, spatial gate or corrected light curve is introduced.

This executes the conditional retained-data branch declared in
LS8AM_INPUT_SCOPE.md and LS8AM_PAIRED_IMAGE_PROTOCOL.md. It transfers the
unchanged LS8U/LS8AH duration-aware method and independent mathematical
functions to all three existing 41-second positive contexts. This is a
retrospective descriptive study, not a new classifier or calibration.

Audited L2 source: 36d081fac65ca35bccbfde5220660fd547d44bc9.
Audited image source: b1e41666134779895f8ed643ddb71e00b74a0816.

| Representative | Exact visit | Native event row | Retained native context | Duration |
|---|---|---:|---|---|
| TG000801_P0 | CH_PR100041_TG000801_V0300 | 223 | 209:238, 29 rows | 1 row / 41 s |
| TG000801_P1 | CH_PR100041_TG000801_V0300 | 363 | 349:378, 29 rows | 1 row / 41 s |
| TG001401_P0 | CH_PR100041_TG001401_V0300 | 178 | 164:193, 29 rows | 1 row / 41 s |

Every event is local row 14. Native training is local 0:12 and 17:29, with
two guards on each side. NEXP=1 for both visits. Include both CAL/COR and
both C0/C1 for every context. Retained CAL/COR payload is 55,680,000
uncompressed bytes. **New archive/source bytes: zero.** The contexts in the
first visit are disjoint; both visits' complete representative sets remain
included without ranking the three by their eventual residuals.

All inputs and code dependencies are pinned in config/ls8an_residuals.json.
Verify the complete LS8AM image manifest and the raw cube digests before use.
Keep original finite masks, centers, radius-25 apertures and 30<r<=40 annuli.
No extra pixels, visits, raw imagettes, recentering or masking are permitted.
Original L2 scores, thresholds and all LS8AM labels remain unchanged.

## Unchanged temporal and spatial method

The exact construction is inherited from LS8U_RESIDUAL_NOISE_PROTOCOL.md and
the pinned cheops_duration_noise, cheops_residual_noise and
cheops_three_sum_noise modules. The only native duration is d=1 and its nominal
cadence is 41 seconds. Use actual BJD times and training-only median-centered
linear pixel baselines. For training n, centered times u and target-time sum q,
the residual weights are 1 on the target, -d/n-q*u/sum(u²) on training and zero
elsewhere. Retain the exact IID multiplier wᵀw.

Also retain the original training-only pooled lag-1/lag-2 covariance model:
50/50 per-pixel/median variance shrinkage, common biased autocorrelation
denominator, Bartlett tapers 2/3 and 1/3, and cadence segments broken outside
0.5–1.5 nominal steps. Missing training rows are not compressed together.
Require positive eigenvalues and positive finite h=wᵀRw and b=trace(MR_train)
without floors or repairs. Event variance is h times the shrunk SSE/b.
Report correlated and IID references, row weights, lags, segmentation and
all propagation factors. This separable estimate does not calibrate tails,
nonstationarity, longer correlations or template-estimation uncertainty.

Use the unchanged weighted scaled-SVD fits for brightness+constant,
gradients+constant and their combination. Templates, gradients, variances
and covariance use training alone. Preserve coefficients, flux/noise,
weighted/unweighted energy and residual/reference ratios. Check native maps
against LS8AM. Report fixed rings 0–8, 8–16 and 16–25 pixels, four quadrants,
top-1/top-10 concentrations and the largest residual coordinate. These are
descriptions, never new selection rules or masks.

Keep the exact C0/C1 boundary identities and signed pixel lists. Project CAL,
COR and DELTA with the same COR combined projector and retain the signed cross
term in E_COR=E_CAL+E_DELTA+2<CAL_residual,DELTA_residual>. These identities do
not partition independent physical causes. Rank-deficient smearing fits remain
unavailable. Missing pixels, rank failures or nonpositive variance stop and
are published without adjusting the method.

## All held controls and signed signal tests

Use all 24 single-row sideband targets. Each excludes itself and two neighboring
rows on each side from the original training set. Native event and native guards
never enter training. Refit temporal trends, templates, variance and covariance
without the held values, retaining original geometric centers and apertures.
This gives **288 held cases**, across all three contexts, both products and
both conventions.
Retain all values and counts at least as large as the native residual/reference
ratio. The controls share training and have different leverage; counts are not
p-values or independent trials.

There are **12 native product/convention cases** across all three contexts. For each, inject both signs
of brightness at 0.001 per exposure, x/y gradients at 0.05 per exposure and
five fixed compact offsets (0,0), (10,0), (0,10), (-10,0), (0,-10).
Compact amplitude is five modeled event-pixel SDs, with unchanged row-major
nearest-pixel tie breaking. Retain **192 signed controls**: 72 known-template
and 120 compact cases. Require known-coefficient and additive-linearity errors
<=1e-9. Report energy and signed-flux retention under hypothetical gradients
plus constant subtraction. No subtraction or veto is adopted.

## Independent audit and stopping rule

Before native calculation, require all **18 inherited known-answer tests**:
eight spatial and ten duration/cadence/guard/serialization/reconstruction tests.
The independent auditor never imports producer modules. Its mathematical
functions and comparison tolerances are AST-identical to LS8AH, with independent
struct decoding, long-double temporal equations, scalar lag sums, explicit
quadratic forms, independent weighted spatial normal equations and coordinate
set accounting. Only source paths, provenance names, fixed counts and the
metadata-established 41-second context cadence change.

Reconstruct every native, held and signed case and all saved arrays. Exact
discrete checks and unchanged numerical tolerances apply: rtol=2e-8,
native atol=1e-6 and dimensionless atol=1e-8. Preserve any failure without
changing tolerances or rerunning native production merely to seek a pass.
Use Python 3.12.14, pinned requirements_ls7g.txt and one BLAS thread.
Publish all outcomes, inputs-by-reference, arrays, logs, environment, freeze
identity, checksums and one six-panel COR residual/control figure per context.
Inspect all three figures before final interpretation; CAL remains fully retained.

**This single bounded study closes regardless of result.** All three original
positives stay unresolved under LS8AM's fixed gates; no qualified candidate,
detector, sensitivity or observing coverage is added. Do not widen or tune
HD 106315 further. Its two eligible visits are already represented here.
Next is rank-14 **WASP-103**, exact chronological pair
CH_PR100013_TG000101_V0300 and CH_PR100013_TG000102_V0300, under a separate
metadata/header freeze followed by exact L2 ranges. Those values remain unopened;
the remaining nine eligible WASP-103 visits stay outside that pair.
Earlier closed studies and reserved TESS/M43 panels remain closed. Calibration
is NOT_READY and its request unsent. Standing publication authority continues;
delegation remains deferred.
