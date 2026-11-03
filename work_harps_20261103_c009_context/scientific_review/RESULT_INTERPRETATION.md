# C009 scientific interpretation

**The C009 discovery core does not show the same-shape barycentric recurrence seen in the preceding contexts.** All six other epochs have negative core Pearson correlations with the fixed March 2023 discovery, even though their surrounding spectra align closely in barycentric coordinates. The distinction between the original core and its surroundings is the main result. **V2E2-0050 remains U.** The bounded comparison does not identify a physical origin, establish a qualified laser candidate or calibrate a null result.

The exact method was public and read back before computation at commit `d1405bf95678d8225c18dc869d0de4b45c2fec76`, with PLAN SHA-256 `b66a3428c61fd703d17526ce0642246f8262aa612f6cc1b68167dab2e92e0b66`. Its single released execution retains 16 measured profiles and 32 comparisons, including four identical-product self rows, eight bounded source windows and one exact historical raw-panel copy. Every profile and comparison is evaluable; none is raw-only, blocked or structurally excluded. The self rows add no independent recurrence evidence.

## Original core and surrounding structure give different results

Each range below includes all six other epochs against the sole discovery reference, with self rows excluded.

| Frame | Region | Raw Pearson r range | Normalized RMS range |
|---|---|---:|---:|
| barycentric | Original core | -0.535854–-0.137821 | 0.024388–0.027060 |
| barycentric | Surrounding pattern | 0.926466–0.959194 | 0.010875–0.014716 |
| topocentric | Original core | -0.273291–0.368757 | 0.020515–0.050972 |
| topocentric | Surrounding pattern | -0.184742–0.214778 | 0.041427–0.059340 |

All six barycentric core correlations are negative, spanning **−0.535854 to −0.137821**, with median **−0.359007**. Every corresponding fixed topocentric core r is higher, with median **0.031288**. The core RMS ordering is mixed: topocentric RMS is lower for January 2022, March 2022, May 2022 and December 2022; barycentric RMS is lower only for May and July 2023. No epoch, sign or unfavorable comparison is removed.

The core figure shows the discovery's positive central enhancement at the catalog position, whereas the other six barycentric profiles show a shallower dip or weak variation there. Their failure to reproduce the discovery crest is retained directly. This is a description of these exact saved windows, not a calibrated non-recurrence probability or proof that a transient has a particular origin. The low-contrast, nearly level reference-scaled core also explains why a small absolute RMS can coexist with a negative Pearson correlation: RMS measures absolute scaled differences, while Pearson compares variation around each mean. Neither statistic is a formal significance test.

The surrounding pattern behaves differently. All six barycentric surrounding comparisons have higher r and lower normalized RMS than their fixed topocentric counterparts, with median barycentric r **0.941731** versus **−0.107914** topocentric. The broad figure retains common dips near −1 Å and a deep pair toward the positive end of the window, together with weaker surrounding structure. Those large shared structures contribute to the surrounding statistic. Their recurrence cannot be transferred to the discovery core or used to claim that its positive enhancement repeats.

The sole discovery reference remains fixed; no alternate reference, fitted lag, recentered core, continuum model, feature subtraction or window variation was tried. Differences between the two core metrics and between core and surroundings are part of the result rather than reasons to select another variant.

## Support, signed values and reference levels

All 16 profiles have 601 finite raw and normalized grid points, valid positive two-flank references and false low-reference flags. Every signed source-window and separate flank nonpositive fraction is zero, and every profile has zero finite positive ERR samples. All comparison rows use all 51 core or 550 surrounding points, above the unchanged minima of 41/440. Support and positive normalization establish availability of these descriptors, not calibrated physical uncertainty.

The merged references span **4,359.610107–13,353.174316 ADU**, and their descriptive first-difference proxies **35.452929–77.439147 ADU**. The discovery merged pooled reference is **12,968.846680 ADU barycentric / 12,966.882812 ADU topocentric**. Its left/right medians are **12,955.453125 / 13,028.172852 ADU** in the barycentric window and **12,953.569824 / 13,028.044922 ADU** in the topocentric window. The small frame-dependent change follows the fixed native-sample masks and is retained.

The fixed positive reference flank includes the strong neighboring absorption-like dips visible near the positive window edge; all such structure remains in the pooled sample median. Even when the left and right medians are similar, these are descriptive reference levels rather than established line-free continua. The scaled discovery crest is not a calibrated emission-line flux or formal detection significance. Positive scalar division leaves Pearson unchanged, while normalized heights and RMS depend on the chosen fixed references. No clipping, sign change, moved flank or masking was used.

Native order 70 has 80 finite left-flank and 81 finite right-flank source samples. Its left/right medians are **24,252.917969 / 23,634.173828**, pooled reference **24,000.388672** and first-difference proxy **201.786106** in unspecified extracted units, in both frames. Native BUNIT is absent; these units differ from merged ADU. No physical flux ratio is inferred. The missing positive ERR support and descriptive proxy do not supply an uncertainty model, sensitivity estimate, false-alarm probability or calibrated survey null.

## Native extraction and historical raw evidence

Fresh checks of all 72 native orders identify order 70 alone covering the original center, with complete context and flanks in both frames. Native-to-merged core r is **0.989623 barycentric / 0.989627 topocentric**, with normalized RMS **0.002944 / 0.002902**. Surrounding r is **0.957015 / 0.957024**, with RMS **0.012147 / 0.012150**. The native figure retains the central discovery enhancement and surrounding dips in both extractions, including their small differences. These are products of the same observation and extraction lineage; their agreement is dependent evidence and supplies no second detection.

The complete raw cutout and historical excess map retain a central vertical band together with much brighter far-right structures that dominate the frozen full scales. The central residual/concentration is faint on those full scales. That visibility limitation is kept separate from the historical enlarged-center descriptions: primary review recorded a compact slanted asymmetric concentration and provisionally voted **A**; secondary review also voted **A** but described broader residuals and explicitly could not exclude an underlying spectral contribution. The root reviewer conservatively adopted **U** for a possible artifact/spectral blend. All three stages remain explicit, and the adopted U governs the current disposition.

The full-panel faintness does not establish absence of the historical central structure or determine its origin. The far-right structures are not newly assigned to the catalog feature. No new crop, contrast variation, pixel statistic, registration, background subtraction or detector model was computed. All four historical global, original local, original baseline and later five-window mapping flags are true for order 70, but those are existing diagnostics rather than a new mapping or origin validation.

The current combination—unreproduced discovery core, recurrent surrounding pattern, shared native enhancement and historical compact-plus-broad residual ambiguity—does not resolve the artifact/spectral mixture. It preserves the original U without silently substituting either old A vote, qualifying a laser candidate or treating a morphology label as proof.

## Fixed frame and prior-data dependence

The discovery observed on 2023-03-22, BERV **3.26509772194068 km/s**, defines the wavelength-specific topocentric anchor **6801.945918689643 Å**. The expected barycentrically coherent catalog center lies outside the fixed ±0.25 Å topocentric core for January 2022 (−0.609655 Å), May 2022 (+0.502722 Å), December 2022 (−0.615032 Å), May 2023 (+0.627913 Å) and July 2023 (+0.737456 Å). March 2022 (−0.170307 Å) and the discovery remain inside. These are prospective metadata coordinates, not fitted peak positions. A higher topocentric core correlation can compare neighboring structure in a displaced epoch; it is not evidence by itself of a stationary detector feature or a physical-origin classification. The 59.6098131157401 km/s BERV span is coordinate separation, not calibrated origin discrimination.

The C009 window [6799.02,6805.02] Å is disjoint from completed C001–C008 bounded windows. Original epoch/profile and raw investigations of 0050 already existed, and all seven observations are reused. Distinct wavelength context does not make the analysis blind, untouched or independent observing evidence and adds no observing time or archive completeness. The catalog fixed-template width is not a measured physical linewidth.

## Verification and next fixed queue item

All four figures were visually inspected, including the complete core legend, the broad pattern, the native/merged panels and the entire raw/excess pair. All PNGs fully decode and match the immutable plot index. All **46 frozen source bindings and 35 numerical output hashes** remain exact. Independent reconstruction passes **428 checks across 63,354 scalar values** without importing production functions. It verifies computational consistency, not human peer review or independent observations.

Before C009 values, the next original remaining queue item was frozen as **C010 / V2E2-0086**, row 23, at exact catalog center **3823.0649999999996 Å**. It changes target to **HD112410** and uses seven existing target-specific epochs with April 2025 discovery BERV **3.40485846065643 km/s** and span **21.30284860830273 km/s**. The old primary/secondary/adopted U and original order 1 local/baseline mapping failures remain explicit. No HD106515A cohort or numeric anchor is transferred, and no C010 analysis was executed here.
