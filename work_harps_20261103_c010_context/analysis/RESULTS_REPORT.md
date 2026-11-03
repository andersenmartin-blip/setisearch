# C010: HD112410 individual spectral context

**All six other HD112410 epochs align better with the fixed discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0086 remains U.** The central broad structure and its surrounding pattern are present with substantial shape, amplitude and reference-level differences. The comparison describes these saved spectra; it does not identify a line or physical origin, qualify a laser candidate, establish significance or calibrate a null result.

The released one-shot execution completed on **2026-11-03 at 08:58:03 UTC**: **16 profiles and 32 comparisons**, including four identical-product self rows, eight bounded source windows and one exact historical raw-panel copy. All statistics are evaluable. All profiles have full support and positive reference medians, while **every profile retains some nonpositive signed source samples**. The sole reference is the discovery observed on 2025-04-29. No new acquisition or observing time was added.

## Target-specific cohort and complete frame comparisons

This phase changes target to **HD112410** and uses its own seven observations from April–August 2025. The previous HD106515A products, reference, numeric anchor and BERV span are not transferred. The original catalog float **3823.0649999999996 Å** is retained in the code and plan; figures display 3823.065 Å for readability. The coordinate is a catalog input, not a measured physical linewidth or a claim of that many digits of wavelength accuracy.

Values separated by `/` below are barycentric/topocentric. Every row uses the one unchanged discovery reference and excludes the self rows.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2025-05-28 | 0.597206 / 0.323374 | 0.836596 / 0.583838 | 1.600996 / 1.811756 | 0.675335 / 0.899235 |
| 2025-05-30 | 0.869229 / 0.106570 | 0.962802 / 0.566657 | 0.495566 / 1.247975 | 0.225915 / 0.752227 |
| 2025-06-22 | 0.796051 / -0.130725 | 0.942073 / 0.450967 | 0.734946 / 1.396688 | 0.344332 / 0.889070 |
| 2025-06-27 | 0.596420 / 0.035152 | 0.882720 / 0.458106 | 1.040796 / 1.360683 | 0.484122 / 0.910905 |
| 2025-07-09 | 0.704257 / -0.095598 | 0.891540 / 0.446920 | 0.911898 / 1.365171 | 0.471502 / 0.921135 |
| 2025-08-07 | 0.859664 / 0.018894 | 0.907357 / 0.453444 | 0.542141 / 1.155767 | 0.428794 / 0.903141 |

| Frame | Region | Nonself raw r range | Median raw r | Nonself normalized RMS range |
|---|---|---:|---:|---:|
| barycentric | Core | 0.596420–0.869229 | 0.750154 | 0.495566–1.600996 |
| barycentric | Surroundings | 0.836596–0.962802 | 0.899448 | 0.225915–0.675335 |
| topocentric | Core | -0.130725–0.323374 | 0.027023 | 1.155767–1.811756 |
| topocentric | Surroundings | 0.446920–0.583838 | 0.455775 | 0.752227–0.921135 |

Barycentric r is higher and normalized RMS lower in **all six pairs in each region**. This is a descriptive contrast under the fixed method, not a calibrated origin discriminator. The spread remains important: **June 27 has the lowest barycentric core r, 0.596420**, while **May 28 has the largest barycentric RMS, 1.600996 in the core and 0.675335 in the surroundings**. May 30 is the highest-correlation barycentric comparison in both regions. No weaker epoch was removed. The four self rows remain at r≈1 and RMS=0 to floating-point precision and add no recurrence evidence.

- [All seven epochs: full signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: original core](results/figures/MERGED_CORE_CONTEXT.png)

The core figure retains the broad central rise, neighboring variation and different exposure levels. The discovery has the strongest raw central crest, while scaled peak heights vary substantially; May 28 appears especially jagged and high after division by its weaker reference level. The broad figure retains several repeated peaks and near-zero troughs, including structure within the reference flanks. Those surrounding features contribute to the broad statistic and are not a separate test of an isolated central emission line. The marker is the catalog/discovery coordinate rather than a fitted peak in every epoch. No fitted center, width, lag, stellar velocity, background, continuum, drift or selected frame shift was tried.

## Fixed geometry and the near-edge epochs

The April 2025 discovery BERV **3.40485846065643 km/s** gives the wavelength-specific topocentric-air anchor **3823.0215804708346 Å**. The fixed ±3 Å context has 601 grid centers at 0.01 Å spacing, with 51 in the original ±0.25 Å core and 550 outside that core. Minimum common support remains 41/440. HD112410's own BERV span is **21.30284860830273 km/s**.

These positions were calculated from metadata before the observed values were read, assuming a barycentrically coherent catalog center. They are predicted coordinates rather than fitted peak positions.

| Observation (UTC) | Role | Predicted offset from fixed anchor (Å) | Original ±0.25 Å core |
|---|---|---:|---|
| 2025-04-29 | Discovery | +0.000000000 | Inside |
| 2025-05-28 | Other epoch | +0.113353068 | Inside |
| 2025-05-30 | Other epoch | +0.120805800 | Inside |
| 2025-06-22 | Other epoch | +0.195252249 | Inside |
| 2025-06-27 | Other epoch | +0.209017539 | Inside |
| 2025-07-09 | Other epoch | +0.237728523 | Inside |
| 2025-08-07 | Other epoch | +0.271674988 | Outside |

**Only August 7 has its predicted center outside the fixed topocentric core**, at +0.271674988 Å: just **0.021674988 Å beyond** the positive edge. July 9 remains inside at +0.237728523 Å, only **0.012271477 Å inside** that edge. This center flag does not say that a whole finite-width feature is inside or outside; the fixed window can retain portions of an extended structure. No boundary was changed. The other epochs remain inside. Frame displacement and the BERV span provide geometry, not calibrated physical-origin evidence. [Prospective coordinates and caveats](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Signed samples, positive references and uncertainty limits

All **16 profiles have 601 finite raw and normalized grid values**, positive valid two-flank references and false low-reference flags. All 32 Pearson and 32 normalized RMS values use complete 51-point core or 550-point surrounding support. No missing-coverage or gap mask is present. Every profile has **zero positive finite ERR samples**.

Positive pooled references do not make every signed source sample positive. **All 16 profiles contain nonpositive source samples**, which remain unchanged. The table retains original-source counts, distinct from interpolated grid counts. Each cell lists **barycentric; topocentric** counts as nonpositive/finite source samples. Frame rows for the same exposure are dependent.

| Source / observation (UTC) | Window nonpositive B; T | Left flank nonpositive B; T | Right flank nonpositive B; T |
|---|---:|---:|---:|
| Merged 2025-04-29 | 2/600; 2/600 | 2/150; 2/150 | 0/150; 0/150 |
| Merged 2025-05-28 | 21/600; 21/600 | 12/150; 11/150 | 8/150; 8/150 |
| Merged 2025-05-30 | 8/600; 8/600 | 4/150; 4/150 | 4/150; 4/150 |
| Merged 2025-06-22 | 6/600; 6/600 | 5/150; 2/150 | 1/150; 1/150 |
| Merged 2025-06-27 | 7/600; 7/600 | 5/150; 2/150 | 2/150; 2/150 |
| Merged 2025-07-09 | 4/600; 4/600 | 2/150; 1/150 | 2/150; 2/150 |
| Merged 2025-08-07 | 10/600; 10/600 | 9/150; 3/150 | 1/150; 1/150 |
| Native order 1, 2025-04-29 | 3/562; 3/562 | 3/139; 3/139 | 0/143; 0/143 |

Merged window fractions range from **2/600 (0.3333%) to 21/600 (3.5%)**. The maximum is May 28 in both frames. Native order 1 retains **3/562 (0.5338%)** in each frame window and **3/139 (2.1583%)** in its left flank. Some left-flank counts change between frames because their fixed source masks differ. Every signed value is preserved without clipping, sign changes or a moved reference region.

Merged pooled references span **59.985079–219.432755 ADU**, with descriptive first-difference proxies **16.159889–23.525127 ADU**. May 28 has the weakest barycentric reference, **59.985079 ADU**, with proxy **16.266478 ADU**; the fixed low-reference test is still false. That flag is not a general quality certificate or formal SNR. Different reference levels affect scaled peak heights and RMS; they do not supply a calibrated emission strength.

The discovery reference values are:

| Product and units | Frame | Finite flank samples L/R | Left-flank median | Right-flank median | Pooled reference | First-difference proxy |
|---|---|---:|---:|---:|---:|---:|
| Merged (ADU) | barycentric | 150 / 150 | 192.890640 | 278.714310 | 219.432755 | 23.324425 |
| Merged (ADU) | topocentric | 150 / 150 | 192.890640 | 278.714310 | 219.432755 | 23.324425 |
| Native order 1 (unspecified) | barycentric | 139 / 143 | 180.737869 | 295.197479 | 216.662064 | 25.384953 |
| Native order 1 (unspecified) | topocentric | 139 / 143 | 180.737869 | 295.197479 | 216.662064 | 25.384953 |

The flanks are structured, with near-zero troughs visible in both sides of the broad context. All fixed native samples in those flanks remain in the pooled medians. These are descriptive reference levels rather than established line-free continua or fitted baselines. Positive scalar division leaves Pearson unchanged, while scaled heights and normalized RMS depend on the chosen fixed levels. Native BUNIT is absent, so native extracted units remain unspecified and distinct from merged ADU. Missing positive ERR and descriptive first-difference proxies provide no formal uncertainty model, false-alarm probability, sensitivity estimate or qualified survey null.

## Native extraction and historical raw mapping limits

Fresh checks of all 72 native orders identify **order 1 alone** covering the center, with complete contexts and both flanks in each frame. Its same-exposure native/merged comparisons are:

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 1 | 0.999254 / 0.999254 | 0.995881 / 0.995881 | 0.052452 / 0.052452 | 0.085030 / 0.085032 |

[Native order 1](results/figures/NATIVE_ORDERS_1.png) retains the broad central structure and neighboring peaks/troughs, following the merged shape closely with small scaled differences. Native and merged extractions share one observation and pipeline lineage. This is dependent evidence, not a second detection, physical flux ratio or validation of the raw-detector registration.

[The complete historical raw cutout and excess map](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) show a central vertical band and bright diffuse patch, with positive and negative residual lobes. Weaker right-edge structure remains present. The central context and weaker edge structure remain on the same complete saved scales. All saved pixels, the historical subtraction and separate complete scales are retained. No new crop, contrast variant, pixel statistic, registration, subtraction, background or detector model was applied.

**Original local mapping and baseline verification remain false for order 1**, alongside true global-grid and later five-window diagnostics. The later supported reference window does not retroactively repair those original limits. Fresh wavelength coverage and native/merged similarity do not establish new raw mapping or physical origin. Historical primary, secondary and adopted reviews all remain **U**, describing broad diffuse trace-confined structure without an unambiguous compact charge deposit. The displayed patch does not change those adopted reviews or qualify a laser candidate.

## Dependence, verification and continuation

This target-specific window is disjoint from the completed C001–C009 bounded windows. Original HD112410 epoch/profile and raw evidence already existed for 0086, and its own seven observations are reused. The distinct target/cohort therefore adds no observing time or archive-wide completeness and is not blind, untouched or independent new observing evidence. All original classifications and completed outputs remain unchanged.

The [independent arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **432 checks across 63,469 scalar values**, reconstructing all eight source windows, 16 profiles, 32 comparisons, one exact raw copy and four self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Maximum wavelength difference is **4.547e-13 Å**, so wavelength arrays are not bitwise exact. Maximum raw interpolation difference is **2.460e-09 native units**, normalized difference **1.135e-11** and comparison difference **4.113e-14**. Computational agreement does not establish physical origin.

The method was public and read back before execution in commit `acb3a382b43ca0b9d3d13f3e30317383f591fb10`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [all profile metrics](results/PROFILE_METRICS.csv), [all comparisons](results/COMPARISONS.csv) and [numerical hashes](results/OUTPUT_HASHES.json) bind the run.

All four figures were visually inspected and fully decoded with their hashes/sizes checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **47 frozen source bindings and 35 numerical output files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records those checks. The next original-queue item is **C012 / V2E2-0087 on HD112410 at 3869.2675 Å**, row 24 / R013. It precedes C011 by queue order and reuses the same target cohort/discovery; a new wavelength-specific anchor and fresh covering-order checks are required. [Next fixed-queue metadata](../scientific_review/NEXT_GROUP_METADATA.json) preserves those dependencies. No C012 analysis was executed here.
