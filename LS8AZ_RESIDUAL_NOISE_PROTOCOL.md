# LS8AZ — retained GJ 536 unresolved-set residual and noise study

23 September 2026. **FROZEN BEFORE NEW NATIVE DERIVED CALCULATION**.
Publish protocol, configuration, producer, independent auditor, report and
workflow together before execution. Require Actions GITHUB_SHA to equal the
clean tracked freeze checkout; verify every input pin before use.

## Specific limitation and complete unresolved scope

LS8AX supplied 4,254 rows and 10,215 eligible overlapping windows. Its complete
signed set has eight positive and one negative representatives; all nine have
completed LS8AY image follow-up. Outcomes: three CORRECTION_LINKED
(TG023501_P3, TG023501_N0, TG007801_P0), four SPATIALLY_STRUCTURED
(TG023501_P0/P2/P4/P5), and two unresolved positives (TG023501_P1/P6).
All 122,580 L2 comparisons and 2,393 metadata checks pass. Eleven image tests
pass before pixels. The independent image audit passes 850,833 numerical and
1,445,201 exact checks, without disagreement. All ten L2/image figures have
been visually inspected and all 280 new scientific files have been locally
verified against their public Git identities. This study again verifies the
entire image manifest. The initial AX checkout timeout acquired no archive
bytes; its preserved failure and prospective checkout recovery are documented
in LS8AX_CHECKOUT_RECOVERY.md. The later data-reading workflows all succeeded.

Both unresolved apertures are complete and retain the original positive sign.
Neither descriptive image gate passes:

| Representative | DELTA/COR C0 / C1 | Column DELTA/COR C0 / C1 | COR displacement explained C0 / C1 | COR brightness explained C0 / C1 |
|---|---:|---:|---:|---:|
| TG023501_P1 | -0.060327 / -0.060201 | -0.058709 / -0.057829 | 38.88464% / 38.87776% | 4.65712% / 4.64243% |
| TG023501_P6 | -0.051018 / -0.050770 | -0.024471 / -0.024280 | 70.41623% / 70.43642% | 55.16456% / 55.27847% |

The largest L2 peak, P6, coincides with a broad oblique bright band crossing the
saved subarray and source aperture in both CAL and COR. DELTA is weaker on the
common scale. P1 shows weaker mixed signed structure over the stellar profile.
These observations do not assign a physical cause, establish a clean point
source brightening, or replace the fixed image gates. No band-specific model,
mask or selected pixels will be introduced. Smearing regressions remain rank
deficient and unavailable.

The limitation is the unknown size/distribution of the remaining residual
relative to local variability, including exact C0/C1 boundary contributions.
The existing fits do not establish a unique cause or calibrated significance.
This executes the conditional retained-data branch declared before pixels.
Use **every unresolved LS8AY representative, P1 and P6**, irrespective of its
L2 rank or eventual residual. The other seven representatives keep their
original labels and receive no new native fitting. Both producer and independent
auditor verify the entire nine-ID/label ledger and derive exactly the frozen
unresolved set before analysis. No event is selected using a residual outcome.

Audited L2 source: a5e343f7b5b6fee73514f2d06bda8e2b64feb85b.
Audited image source: ccd3645aaecd6d79c34d2ccdf800e9609e68ec72.

| Representative | Exact visit | Native event row | Original context | Duration |
|---|---|---:|---|---|
| TG023501_P1 | CH_PR100011_TG023501_V0300 | 1849 | 1835:1864, 29 rows | 1 row / 40.1699981689453 s |
| TG023501_P6 | CH_PR100011_TG023501_V0300 | 3408 | 3394:3423, 29 rows | 1 row / 40.1699981689453 s |

The contexts are disjoint. Each event is local row 14, with training 0:12 and
17:29 and two guards each side. NEXP=1; cadence is verified against its own
L2 header, not copied from another visit. Include both CAL/COR and C0/C1 for
both contexts: 37,120,000 uncompressed retained CAL/COR bytes. **New archive
bytes: zero.** Pin all dependencies and verify the complete LS8AY manifest and
raw cube digests before use. Preserve masks, centers, radius-25 apertures and
30<r<=40 annuli. No extra pixels, visits, raw imagettes, recentering or masking.
All LS8AX scores and thresholds and all nine LS8AY labels remain unchanged.

## Unchanged temporal and spatial method

The exact construction is inherited from LS8U_RESIDUAL_NOISE_PROTOCOL.md and
the pinned cheops_duration_noise, cheops_residual_noise and
cheops_three_sum_noise modules. The only native duration is d=1 and its nominal
cadence is 40.1699981689453 seconds. Use actual BJD times and training-only
median-centered linear pixel baselines. For training n, centered times u and
target-time sum q, residual weights are 1 on the target, -d/n-q*u/sum(u²) on
training and zero elsewhere. Retain the exact IID multiplier wᵀw.

Retain the original training-only pooled lag-1/lag-2 covariance model:
50/50 per-pixel/median variance shrinkage, common biased autocorrelation
denominator, Bartlett tapers 2/3 and 1/3, and cadence segments broken outside
0.5–1.5 nominal steps. Missing training rows are not compressed together.
Require positive eigenvalues and positive finite h=wᵀRw and b=trace(MR_train)
without floors or repairs. Event variance is h times the shrunk SSE/b.
Report correlated and IID references, row weights, lags, segmentation and
all propagation factors. This separable estimate does not calibrate tails,
nonstationarity, longer correlations or template-estimation uncertainty.

Use the unchanged weighted scaled-SVD fits for brightness+constant,
gradients+constant and their combination. Templates, gradients, variances and
covariance use training alone. Preserve coefficients, flux/noise,
weighted/unweighted energy and residual/reference ratios. Check native maps
against LS8AY. Report fixed rings 0–8, 8–16 and 16–25 pixels, four quadrants,
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
both conventions. Retain all values and counts at least as large as the native
residual/reference ratio. The controls share training and have different
leverage; counts are not p-values or independent trials.

There are **eight native product/convention cases**. For each, inject both signs
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
to LS8AS. Adaptations are source paths/provenance, the complete unresolved-set
selection, verified 40.1699981689453-second cadence and fixed counts.

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
labels remain unresolved, all other seven image labels remain unchanged, and
no detector, candidate, sensitivity or observing coverage is qualified.
Do not widen or tune GJ 536 further; its three later eligible visits remain
outside the closed pair. Prepare LS8BA for rank-21 2MASS J11285624+1010395,
exact first pair CH_PR100018_TG010801_V0300 and
CH_PR100018_TG010802_V0300, under separate header/metadata and L2 freezes.
Its science values remain unopened. Closed WASP-103, HD 106315, GJ 581 and
all prior bounded studies and labels stay unchanged, as do reserved TESS/M43
panels. Calibration NOT_READY; request UNSENT. Standing publication
authorization continues; delegation remains deferred.
