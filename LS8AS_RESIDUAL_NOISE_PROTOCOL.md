# LS8AS — retained GJ 581 unresolved-set residual and noise study

22 September 2026. **FROZEN BEFORE NEW NATIVE DERIVED CALCULATION**.
Publish protocol, configuration, producer, independent auditor, report and
workflow together before execution. Require Actions GITHUB_SHA to equal the
clean tracked freeze checkout; verify every input pin before use.

## Specific limitation and complete unresolved scope

LS8AQ supplied 3,623 rows and 7,869 eligible overlapping windows. Its complete
signed set has nine positive and five negative representatives; all 14 have
completed LS8AR image follow-up. Outcomes: nine CORRECTION_LINKED (four positive,
all five negative), three SPATIALLY_STRUCTURED (P2/P6/P8), and two unresolved
positives (P3/P5). All 94,428 L2 comparisons and 3,723 metadata checks pass.
Eleven image tests pass before pixels. The independent image audit passes
1,323,518 numerical and 2,248,091 exact checks, without disagreement. All 15
L2/image figures have been visually inspected. All 273 new scientific files
have public identities; 245 were locally Git-verified. The 28 larger compressed
CAL/COR inputs were independently checksum-verified and struct-decoded by the
successful workflow. This study again verifies the entire image manifest.

Both unresolved apertures are complete and retain the original positive sign.
Neither descriptive image gate passes:

| Representative | DELTA/COR C0 / C1 | Column DELTA/COR C0 / C1 | COR displacement explained C0 / C1 | COR brightness explained C0 / C1 |
|---|---:|---:|---:|---:|
| TG023701_P3 | -0.036878 / -0.036430 | -0.040257 / -0.039597 | 42.46252% / 42.55592% | 10.13317% / 10.13718% |
| TG023701_P5 | +0.368764 / +0.390035 | +0.372081 / +0.393790 | 16.68186% / 16.36840% | 6.18916% / 6.05217% |

Both images show signed structure over the stellar profile in CAL and COR;
the DELTA map is weaker on the common scale. This does not replace the fixed
80% displacement gate or assign a cause. Smearing regressions remain rank
deficient and unavailable.

The limitation is the unknown size/distribution of the remaining residual
relative to local variability, including exact C0/C1 boundary contributions.
The existing fits do not establish a unique cause or calibrated significance.
This executes the conditional retained-data branch declared before pixels.
Use **every unresolved LS8AR representative, P3 and P5**, irrespective of its
L2 rank or eventual residual. The 12 representatives closed by the original
gates keep their labels and receive no new native fitting. In particular,
the two-exposure N1 is already CORRECTION_LINKED; it is not dropped from the
image study or reclassified here. Both producer and independent auditor
verify the entire 14-ID/label ledger and derive exactly the frozen unresolved
set before analysis. No event is selected using any residual-study outcome.

Audited L2 source: 051d973dffe52f151f3948e38070b40bbc32cdf4.
Audited image source: af1de44c32b524d8438adb23e0cf9003928e94b4.

| Representative | Exact visit | Native event row | Original context | Duration |
|---|---|---:|---|---|
| TG023701_P3 | CH_PR100011_TG023701_V0300 | 2528 | 2514:2543, 29 rows | 1 row / 60 s |
| TG023701_P5 | CH_PR100011_TG023701_V0300 | 2761 | 2747:2776, 29 rows | 1 row / 60 s |

The contexts are disjoint. Each event is local row 14, with training 0:12 and
17:29 and two guards each side. NEXP=1. Include both CAL/COR and C0/C1 for both
contexts: 37,120,000 uncompressed retained CAL/COR bytes. **New archive bytes:
zero.** Pin all dependencies and verify the complete LS8AR manifest and raw
cube digests before use. Preserve masks, centers, radius-25 apertures and
30<r<=40 annuli. No extra pixels, visits, raw imagettes, recentering or masking.
All LS8AQ scores and thresholds and all 14 LS8AR labels remain unchanged.

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
against LS8AR. Report fixed rings 0–8, 8–16 and 16–25 pixels, four quadrants,
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
This gives **192 held cases**, across both unresolved contexts, both products and
both conventions.
Retain all values and counts at least as large as the native residual/reference
ratio. The controls share training and have different leverage; counts are not
p-values or independent trials.

There are **eight native product/convention cases** across both unresolved contexts. For each, inject both signs
of brightness at 0.001 per exposure, x/y gradients at 0.05 per exposure and
five fixed compact offsets (0,0), (10,0), (0,10), (-10,0), (0,-10).
Compact amplitude is five modeled event-pixel SDs, with unchanged row-major
nearest-pixel tie breaking. Retain **128 signed controls**: 48 known-template
and 80 compact cases. Require known-coefficient and additive-linearity errors
<=1e-9. Report energy and signed-flux retention under hypothetical gradients
plus constant subtraction. No subtraction or veto is adopted.

## Independent audit and stopping rule

Require all 18 inherited known-answer tests before native calculation: eight
spatial and ten duration/cadence/guard/serialization/reconstruction tests.
No new mathematical module or duration is introduced. All independent audit
functions outside main and the recursive comparison function are AST-identical
to LS8AN. The only adaptations are source paths/provenance, the complete
unresolved-set selection, verified 60-second cadence and fixed counts.

Independently struct-decode cubes and reconstruct every native, held and signed
case and saved array with long-double temporal equations, scalar lag sums,
explicit quadratic forms, independent weighted spatial normal equations and
coordinate-set accounting. Keep rtol=2e-8, native atol=1e-6 and dimensionless
atol=1e-8. Preserve any failure without changing tolerances or rerunning native
production merely to seek a pass. Use Python 3.12.14, pinned requirements and
one BLAS thread. Publish all outcomes, arrays, inputs by reference, logs,
environment, freeze identity, checksums and one six-panel COR figure per
unresolved context. Inspect both figures; CAL remains fully retained.

**This single bounded study closes regardless of result.** Both unresolved
labels remain unresolved, all other 12 image labels remain unchanged, and
no detector, candidate, sensitivity or observing coverage is qualified.
Do not widen or tune GJ 581 further; its five later eligible visits remain
outside the closed pair. Prepare LS8AT for rank-16 EC14599-2047, exact first
pair CH_PR100002_TG010301_V0300 and CH_PR100002_TG010302_V0300, under separate
header/metadata and L2 freezes. Its third eligible visit stays outside the pair
and its science values remain unopened. Closed WASP-103, HD 106315's three
unresolved labels and bounded study, prior studies and reserved TESS/M43 panels
stay unchanged. Calibration NOT_READY; request UNSENT. Standing publication
authorization continues; delegation remains deferred.
