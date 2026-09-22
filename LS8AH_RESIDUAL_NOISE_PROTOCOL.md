# LS8AH — retained PG 1207-033 residual and local-noise study

22 September 2026. **FROZEN_BEFORE_NEW_NATIVE_DERIVED_CALCULATION**.
Publish this protocol, configuration, producer, independent auditor, report
and workflow together before execution. The recorded Actions GITHUB_SHA is
the freeze identity; the producer requires that exact clean tracked checkout.

## Specific limitation and complete scope

LS8AF's 153 rows and 165 eligible overlapping windows have six positive
crossings in one cluster and zero negative crossings. The independent L2
audit passes 1,980 comparisons. Its complete signed representative set has
completed the separately frozen LS8AG image diagnostic and independent audit:
94,537 numerical comparisons and 160,581 exact checks pass without disagreement.
All nine inherited image tests pass. Both the L2 and CAL/COR/DELTA figures
were visually inspected. Twenty of 22 image-manifest entries were additionally
verified locally; the two compressed cubes retain their exact public identities
and are checksum-verified and independently decoded by the image workflow.
This retained-data workflow must verify the complete manifest before use.

TG000901_P0 remains **UNRESOLVED_WITHIN_FIXED_SCOPE**. Both original apertures
are complete and retain the positive L2 sign. DELTA/COR is 0.218211/0.314435;
the column-projected ratios are 0.215029/0.309622, below the fixed 0.5 gate.
COR displacement explained energy is 11.40484%/16.22922%, below 80%, versus
7.95056%/7.20016% for brightness. The smearing regression remains rank deficient.
The figure shows an extended stripe in CAL and COR crossing the upper edge
of the source apertures. This visual description does not identify its cause
or satisfy the specifically frozen displacement-fit gate. CAL aperture sums
are 118,461.357/72,091.340 ADU and COR sums 151,526.034/105,156.047 ADU;
the coordinate-convention sensitivity is retained without choosing a preferred
aperture. DELTA sums are 33,064.677/33,064.707 ADU.

The specific remaining question is the size and spatial distribution of the
unmodeled residual relative to local variability, including the exact C0/C1
boundary contribution. Neither a unique cause nor a calibrated significance
follows from the current fits. No stripe mask or stripe-specific model is added.

This executes the conditional retained-data branch declared in
LS8AG_INPUT_SCOPE.md and LS8AG_PAIRED_IMAGE_PROTOCOL.md. It transfers the
unchanged LS8U duration-aware method, including its independent mathematical
functions, to the one existing 60-second positive context. This is a
retrospective descriptive study, not a new classifier or calibration.

| Item | Fixed value |
|---|---|
| Audited L2 source | `3afc7472cf815da46bdadec8ba0fe5e35528eb63` |
| Audited image source | `45972dd2e8658a2dc743f67b2e790ad6529c456e` |
| Product key | CH_PR100002_TG000901_V0300 |
| Representative | TG000901_P0, positive, native row 60, local row 14 |
| Duration | One 60-second exposure, NEXP=1 |
| Retained context | Native rows 46:75, 29 rows |
| Native training | Local 0:12 and 17:29, with two guards on each side |
| Products and coordinates | Both CAL/COR and both C0/C1 |
| Existing CAL/COR payload | 18,560,000 uncompressed bytes |
| New archive/source bytes | **Zero** |

All inputs and code dependencies are pinned in config/ls8ah_residuals.json.
Verify the complete LS8AG image manifest and the raw cube digests before use.
Keep original finite masks, centers, radius-25 apertures and 30<r<=40 annuli.
No extra pixels, visits, raw imagettes, recentering or masking are permitted.
Original L2 scores, thresholds and the LS8AG label remain unchanged.

## Unchanged temporal and spatial method

The exact construction is inherited from LS8U_RESIDUAL_NOISE_PROTOCOL.md and
the pinned cheops_duration_noise, cheops_residual_noise and
cheops_three_sum_noise modules. The only native duration is d=1 and its nominal
cadence is 60 seconds. Use actual BJD times and training-only median-centered
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
against LS8AG. Report fixed rings 0–8, 8–16 and 16–25 pixels, four quadrants,
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
This gives **96 held cases**, across both products and both conventions.
Retain all values and counts at least as large as the native residual/reference
ratio. The controls share training and have different leverage; counts are not
p-values or independent trials.

There are **four native product/convention cases**. For each, inject both signs
of brightness at 0.001 per exposure, x/y gradients at 0.05 per exposure and
five fixed compact offsets (0,0), (10,0), (0,10), (-10,0), (0,-10).
Compact amplitude is five modeled event-pixel SDs, with unchanged row-major
nearest-pixel tie breaking. Retain **64 signed controls**: 24 known-template
and 40 compact cases. Require known-coefficient and additive-linearity errors
<=1e-9. Report energy and signed-flux retention under hypothetical gradients
plus constant subtraction. No subtraction or veto is adopted.

## Independent audit and stopping rule

Before native calculation, require all **18 inherited known-answer tests**:
eight spatial and ten duration/cadence/guard/serialization/reconstruction tests.
The independent auditor never imports producer modules. Its mathematical
functions are AST-identical to LS8U, with independent struct decoding,
long-double temporal equations, scalar lag sums, explicit quadratic forms,
independent weighted spatial normal equations and coordinate-set accounting.
Only source paths, provenance field names and fixed case counts change.

Reconstruct every native, held and signed case and all saved arrays. Exact
discrete checks and unchanged numerical tolerances apply: rtol=2e-8,
native atol=1e-6 and dimensionless atol=1e-8. Preserve any failure without
changing tolerances or rerunning native production merely to seek a pass.
Use Python 3.12.14, pinned requirements_ls7g.txt and one BLAS thread.
Publish all outcomes, inputs-by-reference, arrays, logs, environment, freeze
identity, checksums and the six-panel COR residual/control figure. Inspect
the figure before final interpretation; CAL results remain fully retained.

**This single bounded study closes regardless of result.** The original
positive stays unresolved under LS8AG's fixed gate; no qualified candidate,
detector, sensitivity or observing coverage is added. Do not widen or tune
PG 1207-033 further. The cohort has only two eligible visits; neither is widened.
Next is rank-11 **EC13080-1508**, exact chronological pair
CH_PR100002_TG005201_V0300 and CH_PR100002_TG005202_V0300, under a separate
metadata/header freeze followed by exact L2 ranges. Those values remain unopened.
Earlier closed studies and reserved TESS/M43 panels remain closed. Calibration
is NOT_READY and its request unsent. Standing publication authority continues;
delegation remains deferred.
