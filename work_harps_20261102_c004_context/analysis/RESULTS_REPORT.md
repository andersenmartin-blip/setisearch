# C004: HD106515A joint spectral context

The central crest, neighboring shoulder and surrounding structured spectrum recur closely in barycentric coordinates across all seven existing target epochs. Each of the three native order 3 extractions also closely follows its same-exposure merged product. **V2E2-0028, V2E2-0045 and V2E2-0052 remain U.** These results describe spectral morphology; they do not establish a line identity, physical origin, qualified laser candidate or calibrated null.

The single released execution completed on **2026-11-02 at 18:34:34 UTC**, producing **20 profiles and 96 comparisons**, including **12 identical-product self-comparisons**. All slots are measured; no source is blocked, raw-only or structurally excluded. There are three distinct, unchanged discovery references: 2022-03-07 (0028), 2023-03-22 (0045) and 2023-05-24 (0052). No new archive acquisition, observing time or archive-wide completeness is claimed.

## Fixed references and all seven epochs

All three catalog centers coincide at **3872.245 Å** in barycentric air wavelengths. The first C004 discovery is **2022-03-07**, with BERV **10.77158288517 km/s** and fixed topocentric anchor **3872.1058747209718 Å**. The full ±3 Å window has 601 centers on a 0.01 Å grid. The original ±0.25 Å core has **51 centers**; the surrounding region has **550**. Minimum common support is 41 and 440, respectively. No center, width, lag, stellar velocity, drift, background or continuum was fitted.

The table retains each discovery reference separately. Each range covers its six nonself epoch comparisons. B/T denotes barycentric/topocentric. The 12 identical-product self rows remain in the complete output at r = 1 and normalized RMS = 0; they add no independent evidence. Reversed discovery pairs and reused epoch profiles are also dependent.

| Reference | Region | Raw r B range | Raw r T range | Normalized RMS B range | Normalized RMS T range |
|---|---|---:|---:|---:|---:|
| 0028 (2022-03-07) | Core | 0.962416–0.990102 | -0.261019–0.297301 | 0.083886–0.154505 | 0.616565–0.717136 |
| 0028 (2022-03-07) | Surroundings | 0.974341–0.995102 | 0.102038–0.357637 | 0.094143–0.190692 | 0.849889–0.998792 |
| 0045 (2023-03-22) | Core | 0.945522–0.990102 | -0.128058–0.748067 | 0.072157–0.178968 | 0.500115–0.678577 |
| 0045 (2023-03-22) | Surroundings | 0.974156–0.995102 | 0.013010–0.244989 | 0.094143–0.187309 | 0.920036–1.063938 |
| 0052 (2023-05-24) | Core | 0.925276–0.988447 | -0.086757–0.748067 | 0.072157–0.213129 | 0.259214–0.683163 |
| 0052 (2023-05-24) | Surroundings | 0.967167–0.993093 | 0.013010–0.459677 | 0.098311–0.217996 | 0.701397–1.051426 |

Across all three references, nonself barycentric core r spans **0.925276–0.990102**, and surrounding r **0.967167–0.995102**. Every one of the 18 nonself source/reference comparisons per region has higher barycentric r and lower barycentric normalized RMS in this fixed calculation. This describes the chosen windows and does not calibrate an origin discriminator. The core figure retains the central multi-sample crest, a lower shoulder near −0.13 Å and neighboring troughs. The broad figure preserves repeated peaks and plateaus across the entire window, including structure within both reference flanks.

- [All seven epochs: broad signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: fixed original core](results/figures/MERGED_CORE_CONTEXT.png)

Both figures retain the full titles and seven-epoch legend with matching scales across frames. The three barycentric markers coincide; their topocentric discovery markers differ. They mark catalog/discovery coordinates and do not track fitted peaks in other epochs. The 0052 marker is outside the fixed topocentric core, and remains visible in the broad figure.

## Fixed topocentric window and displaced references

**The topocentric core is never recentered on a later feature or on a later discovery reference.** The following offsets were calculated from metadata before the observed arrays were read, assuming a barycentrically coherent center. They are coordinate predictions, not fitted peak locations.

| Observation (UTC) | Role | Predicted center offset (Å) | Fixed ±0.25 Å core |
|---|---|---:|---|
| 2022-01-05 | Other epoch | -0.250111086 | Outside |
| 2022-03-07 | 0028 | +0.000000000 | Inside |
| 2022-05-07 | Other epoch | +0.383141520 | Outside |
| 2022-12-31 | Other epoch | -0.253171992 | Outside |
| 2023-03-22 | 0045 | +0.096952368 | Inside |
| 2023-05-24 | 0052 | +0.454409820 | Outside |
| 2023-07-03 | Other epoch | +0.516770410 | Outside |

Five epochs have predicted centers outside the fixed core. For January 2022, the predicted offset **−0.250111086 Å** is only **0.000111086 Å beyond the negative edge**. The exact original boundary remains unchanged; this near-edge classification does not mean that the entire feature lies outside the window. December 2022 is also just beyond that edge. The full seven-epoch BERV span of 59.6098131157401 km/s is coordinate separation, not a calibrated physical-origin test. [All prospective coordinates and assumptions](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

The displacement affects the reference side too: **the 0052 / May 2023 reference center itself is at +0.454409820 Å**, outside the fixed topocentric core. Thus comparisons against that reference may compare neighboring structure on either or both sides. The largest nonself topocentric core r, **0.748067**, belongs to the reversed March 2023/May 2023 discovery pair; its repetition in both reference rows is dependent. The smallest nonself topocentric core RMS, **0.259214**, is July 2023 against May 2023, where both predicted centers lie outside the fixed core. These are not recentered comparisons of the original feature. No alternative anchor or shifted window was tried.

## Signed flux and structured reference levels

All **20 profiles** have complete 601-point raw and normalized support, positive flank references, false low-reference flags and **zero finite positive ERR samples**. Merged reference levels span **151.160–356.546 ADU**, with descriptive first-difference proxies **19.231–44.514 ADU**. A positive pooled reference does not require every signed sample to be positive.

In the May 2022 merged observation, **1 of 600 finite source samples (0.1667%) is nonpositive in each frame's window**. Those two profile rows concern the same exposure. Its topocentric right flank contains 1 of 150 nonpositive samples (0.6667%); the other flank nonpositive fractions are zero. The remaining 18 profiles have zero nonpositive window fractions. All signed values are retained without clipping or sign changes. The fixed pooled medians remain positive and pass the predeclared support gates. The low-reference rule is reference ≤ 3 × the first-difference proxy; these proxies are descriptive and are not formal uncertainties or SNRs.

The current core **was already visible within C003's positive normalization flank**. The C004 core [3871.995, 3872.495] Å lies fully inside that earlier flank [3871.25125, 3872.75125] Å. The broader windows overlap over [3869.245, 3872.75125] Å, a continuous width of **3.50625 Å**. The original queue fixed this continuation, but the flux interpretation is neither blind nor independent of C003, and the same seven observing products are reused.

This dependence is reciprocal: **C003's complete original core union [3869.495, 3870.0075] Å lies inside C004's negative reference flank [3869.245, 3870.745] Å**. That known structure remains in the fixed median without masks or alternative flanks. Both 1.5–3 Å flanks contain spectral structure and are reference levels, not line-free continua. Positive scalar division leaves Pearson unchanged; heights and normalized RMS depend on the selected fixed reference levels.

## Three native extraction contexts

Fresh header checks of all **216 orders** identify only order 3 as covering the feature center in each discovery product. All six native frame profiles have full support. Native BUNIT is absent, so these values retain **unspecified extracted units**, distinct from merged ADU. Values separated by `/` below are B/T.

| Discovery / order 3 | Flank reference B/T | Noise proxy B/T | Nonpositive % B/T | Low flag B/T |
|---|---:|---:|---:|---|
| 0028 (2022-03-07) | 334.995 / 336.476 | 46.352 / 46.569 | 0 / 0 | false / false |
| 0045 (2023-03-22) | 344.239 / 349.586 | 46.894 / 48.258 | 0 / 0 | false / false |
| 0052 (2023-05-24) | 247.025 / 246.907 | 37.025 / 35.887 | 0 / 0 | false / false |

| Discovery / order 3 | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 0028 (2022-03-07) | 0.999621 / 0.999621 | 0.998367 / 0.998366 | 0.031201 / 0.026355 | 0.064481 / 0.060691 |
| 0045 (2023-03-22) | 0.999528 / 0.999765 | 0.998318 / 0.997413 | 0.046926 / 0.059278 | 0.074051 / 0.084486 |
| 0052 (2023-05-24) | 0.999025 / 0.998855 | 0.998162 / 0.997104 | 0.023325 / 0.013208 | 0.046360 / 0.051332 |

All 12 native-to-merged r values span **0.997104–0.999765**. [All three native and same-exposure merged contexts](results/figures/NATIVE_ORDERS_1.png) closely follow one another across the window, with small visible scaled differences, including on the positive-flank plateaus. Shared extraction lineage means this agreement is not independent confirmation, a physical flux ratio or a new raw-detector mapping validation.

## Preserved raw evidence and historical mapping

[All three exact stored raw cutout/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain central vertical bands with brighter central patches, additional right-edge structure and alternating positive/negative residual lobes. The May 2023 central patch is weaker relative to its bright edge structures. Every panel uses its separate full scale; the historical subtraction is unchanged. No detector-origin assignment, new registration, background fit, detector model or pixel statistic is applied.

For **all three records**, historical global, local, baseline and later five-window mapping flags are true and remain distinct stages. These are preserved historical diagnostics, not a new mapping or physical-origin validation. All primary, secondary and adopted reviews remain unchanged. The catalog fixed-template width is not a measured physical linewidth. Missing positive ERR support and descriptive first-difference proxies do not establish significance, false-alarm probability, sensitivity or a survey null. All three U labels remain unchanged.

## Reconstruction and delivery checks

The [independent arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **559 checks across 79,803 scalar values**, covering all ten bounded source windows, 20 profiles, 96 comparisons, three exact raw copies and 12 self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Wavelength differences are at most 4.55×10⁻¹³ Å, so wavelength arrays are not bitwise exact. Maximum raw-profile interpolation difference is 1.95×10⁻⁹ native units, normalized-profile difference 7.50×10⁻¹² and comparison difference 1.34×10⁻¹³.

The exact method was public and read back before execution in commit `7c3e46e41fc98073c844259ab91350b8363bc63a`. The [plan](PLAN.json), [release](ROOT_RELEASE.json), [run summary](results/SUMMARY.json), [bounded input index](results/BOUNDED_INPUT_INDEX.json), [complete profile metrics](results/PROFILE_METRICS.json), [complete comparisons](results/COMPARISONS.json) and [output hashes](results/OUTPUT_HASHES.json) bind the calculation.

All four figures were visually inspected, including the core title and seven-epoch legend at original resolution. Complete PNG decoding, byte sizes and hashes match the unchanged [plot index](results/PLOT_INDEX.json). All **46 frozen method/input sources and 43 numerical output files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records those checks. The next original-queue group is C002; its core was already visible in C003, which must remain explicit in any continuation.
