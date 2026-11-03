# C009: HD106515A individual spectral context

**The discovery core does not show same-shape barycentric recurrence in the six other epochs, while its surrounding spectrum does recur. V2E2-0050 remains U.** All six nonself barycentric core Pearson values are negative. The discovery observation retains a local multi-sample excess near the catalog center, whereas the other barycentric core profiles show different, often depressed structure there. This descriptive difference does not establish physical origin, a calibrated nondetection, a qualified laser candidate or a survey null.

The released one-shot execution completed on **2026-11-03 at 00:23:31 UTC**: **16 profiles and 32 comparisons**, including four identical-product self rows, eight bounded source windows and one exact historical raw-panel copy. All profiles and statistics are numerically evaluable. No profile is raw-only, blocked or structurally excluded. The sole fixed reference is the March 2023 discovery, observed on 2023-03-22. No new acquisition or observing time was added.

## Core and surroundings retain different outcomes

The center is **6802.02 Å** in barycentric air wavelengths. Values separated by `/` are barycentric/topocentric. Each row is one other epoch against the same discovery reference, retaining all six outcomes.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2022-01-05 | -0.535854 / -0.273291 | 0.929412 / -0.184742 | 0.027060 / 0.023754 | 0.014706 / 0.059340 |
| 2022-03-07 | -0.497037 / 0.368757 | 0.959194 / 0.214778 | 0.025714 / 0.024251 | 0.010875 / 0.047549 |
| 2022-05-07 | -0.440688 / 0.027000 | 0.952731 / -0.056444 | 0.025316 / 0.020515 | 0.011669 / 0.051412 |
| 2022-12-31 | -0.147572 / -0.089799 | 0.926466 / -0.182219 | 0.025337 / 0.022159 | 0.014716 / 0.058124 |
| 2023-05-24 | -0.277326 / 0.035576 | 0.956409 / -0.159384 | 0.024861 / 0.029084 | 0.011165 / 0.046737 |
| 2023-07-03 | -0.137821 / 0.116804 | 0.930732 / 0.023927 | 0.024388 / 0.050972 | 0.014085 / 0.041427 |

| Frame | Region | Nonself raw r range | Median raw r | Nonself normalized RMS range |
|---|---|---:|---:|---:|
| barycentric | Core | -0.535854–-0.137821 | -0.359007 | 0.024388–0.027060 |
| barycentric | Surroundings | 0.926466–0.959194 | 0.941731 | 0.010875–0.014716 |
| topocentric | Core | -0.273291–0.368757 | 0.031288 | 0.020515–0.050972 |
| topocentric | Surroundings | -0.184742–0.214778 | -0.107914 | 0.041427–0.059340 |

All six **barycentric core correlations are negative**, and the corresponding topocentric core r is higher in all six cases. Normalized core RMS is lower topocentrically for January, March and May 2022 and December 2022; it is lower barycentrically only for May and July 2023. These two descriptors are retained separately. There is no claim of a coherent topocentric feature, since the fixed window can sample neighboring structure and the core correlations remain mixed.

By contrast, the **surrounding pattern favors barycentric coordinates in all six pairs by both r and normalized RMS**. This comparison includes recurring troughs near approximately −1 Å and +2.4/+2.7 Å and other spectral structure. It does not validate recurrence of the distinct central excess. No surrounding statistic is substituted for a core result. The four self rows remain at r≈1 and RMS=0 to floating-point precision; they add no independent evidence.

- [All seven epochs: full signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: original core](results/figures/MERGED_CORE_CONTEXT.png)

The discovery's scaled core rises locally near the catalog marker; the other barycentric profiles do not reproduce that same shape. The full raw view retains the different exposure flux levels, and the scaled view retains the fixed signed reference division. The marker is the original catalog/discovery coordinate, not a fitted peak. No alternate window, recentering, fitted center, width, lag, stellar velocity, continuum, background or drift was introduced. Neither the visual difference nor the negative correlations supply an event probability, a detection threshold or a quantitative limit on recurrence.

## Fixed frame geometry

The March 2023 discovery BERV **3.26509772194068 km/s** defines the wavelength-specific topocentric-air anchor **6801.945918689643 Å**. The fixed ±3 Å window has 601 centers on a 0.01 Å grid, including 51 in the original ±0.25 Å core and 550 in the surroundings. Common-support minima remain 41/440.

The positions below were calculated from metadata before these values were read, assuming a barycentrically coherent catalog center. They are coordinate predictions, not measured peak locations.

| Observation (UTC) | Role | Predicted offset from fixed anchor (Å) | Original ±0.25 Å core |
|---|---|---:|---|
| 2022-01-05 | Other epoch | -0.609654750 | Outside |
| 2022-03-07 | Other epoch | -0.170307392 | Inside |
| 2022-05-07 | Other epoch | +0.502722409 | Outside |
| 2022-12-31 | Other epoch | -0.615031564 | Outside |
| 2023-03-22 | Discovery | +0.000000000 | Inside |
| 2023-05-24 | Other epoch | +0.627912938 | Outside |
| 2023-07-03 | Other epoch | +0.737456106 | Outside |

Five predicted centers lie outside the fixed topocentric core. Only March 2022 and the March 2023 discovery lie inside. The topocentric window remains fixed, so other comparisons can concern neighboring structure instead of the original catalog feature. The 59.6098131157401 km/s BERV span supplies coordinate separation rather than a calibrated origin discriminator. [Prospective coordinates and caveats](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Signed reference levels and uncertainty limits

All **16 profiles have 601 finite raw and normalized samples**, valid positive two-flank references and false low-reference flags. All source-window and separate-flank nonpositive fractions are zero; signed values were retained without clipping. Every profile has **zero positive finite ERR samples**. All comparisons use their complete 51-point core or 550-point surrounding masks.

Merged reference levels span **4359.610–13353.174 ADU**, with descriptive first-difference proxies **35.453–77.439 ADU**. The reference ≤ 3 × proxy rule is descriptive, not formal SNR. The discovery values are retained separately in each frame:

| Product and units | Frame | Finite flank samples L/R | Left-flank median | Right-flank median | Pooled reference | First-difference proxy |
|---|---|---:|---:|---:|---:|---:|
| Merged (ADU) | barycentric | 151 / 151 | 12955.453125 | 13028.172852 | 12968.846680 | 63.173206 |
| Merged (ADU) | topocentric | 150 / 150 | 12953.569824 | 13028.044922 | 12966.882812 | 64.037793 |
| Native order 70 (unspecified) | barycentric | 80 / 81 | 24252.917969 | 23634.173828 | 24000.388672 | 201.786106 |
| Native order 70 (unspecified) | topocentric | 80 / 81 | 24252.917969 | 23634.173828 | 24000.388672 | 201.786106 |

The discovery center coincides between frames, but ±3 Å and the flank boundaries are defined separately in each frame. Their barycentric widths differ by the fixed BERV factor. The merged discovery therefore has 151 samples per flank barycentrically and 150 per flank topocentrically, with the small reference/proxy differences preserved above; no equality was imposed. Native reference samples remain the same in both frames. Both complete fixed reference flanks remain included. The deep positive-offset troughs fall in the positive reference interval [1.5,3] Å. The pooled medians are descriptive reference levels, not established line-free continua or fitted backgrounds. The plotted normalized excess and RMS depend on these chosen fixed levels. Positive scalar division leaves Pearson unchanged. No emission-line equivalent width, calibrated amplitude or physical linewidth was measured. Native BUNIT is absent, so extracted native values retain unspecified units distinct from merged ADU.

## Native extraction and full preserved raw context

Fresh checks of all 72 native orders identify **order 70 alone** as covering the original center; both complete windows and flanks are retained. The discovery native/merged comparisons are:

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 70 | 0.989623 / 0.989627 | 0.957015 / 0.957024 | 0.002944 / 0.002902 | 0.012147 / 0.012150 |

[Native order 70](results/figures/NATIVE_ORDERS_1.png) retains the discovery local excess and surrounding troughs, following its same-exposure merged extraction closely with visible scaled differences preserved. Shared extraction lineage makes this dependent evidence; an event present in both extractions is not a second observation or a physical-origin validation.

[The complete historical raw cutout and excess map](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain separate full scales. Bright structures at the far right and lower-right edge dominate those scales, while the nominal central band and residual are much fainter. The historical compact slanted concentration review concerns the enlarged central context and coexists with broader residual structure; it does not describe the complete panel's scale. All original pixels and the historical subtraction are preserved. No new spatial model, registration, subtraction, pixel statistic or origin assignment was applied to either the central or edge structures.

**Preserve the historical primary A / secondary A / root-adopted U distinction.** Both reviewers provisionally voted A after describing a compact slanted concentration in order 70. The secondary retained broader residual structure and could not exclude an underlying spectral contribution. Root adopted **U** because a possible artifact/spectral blend remained unresolved. The current adopted code is U; neither the earlier votes, the central non-recurrence nor the surrounding recurrence replaces that adoption or qualifies a laser candidate.

The historical global, local, baseline and later five-window mapping stages are all true. They remain distinct existing diagnostics, not a new mapping test or an origin classification. All primary, secondary and adopted texts, current dispositions and prior outputs are unchanged.

## Dependence, verification and continuation

The C009 window [6799.02,6805.02] Å is disjoint from completed C001–C008 bounded wavelength windows. Original epoch/profile and raw evidence already existed for this record, and all seven observing products are reused. Distinct wavelength context does not make the evidence blind, untouched or independent and adds no observing time or archive-wide completeness. Missing ERR and uncalibrated morphology provide no formal significance, false-alarm probability, sensitivity estimate or qualified survey null.

The [independent arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **428 checks across 63,354 scalar values** without importing production functions, covering all eight source windows, 16 profiles, 32 comparisons, one exact raw copy and four self rows. Source flux, ERR, indices and profile metrics agree exactly. Maximum wavelength difference is **9.095e-13 Å**; wavelength arrays are not bitwise exact. Maximum raw interpolation difference is **1.502e-08 native units**, normalized difference **6.258e-13** and comparison difference **5.218e-15**. Computational agreement does not establish physical origin.

The method was public and read back before execution in commit `d1405bf95678d8225c18dc869d0de4b45c2fec76`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [all profile metrics](results/PROFILE_METRICS.csv), [all comparisons](results/COMPARISONS.csv) and [numerical hashes](results/OUTPUT_HASHES.json) bind the run.

All four figures were visually inspected and fully decoded with sizes and hashes checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **46 frozen method/input source bindings and 35 numerical output files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records delivery checks. The next original-queue item is **C010 / V2E2-0086 on HD112410 at 3823.065 Å**, row 23, selected before C009 values. Its seven existing 2025 epochs and April 2025 discovery reference belong to a different target; no HD106515A products or numerical anchor are transferred. [Next fixed-queue metadata](../scientific_review/NEXT_GROUP_METADATA.json) preserves those identities and historical mapping limits. No C010 analysis was executed here.
