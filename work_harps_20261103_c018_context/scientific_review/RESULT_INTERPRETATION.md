# C018: seven-reference descriptive context on HD114783

The fixed comparison supports a repeatable barycentric spectral pattern across these seven existing observations. Every one of the 42 directed nonself merged comparisons favors the barycentric frame in both raw Pearson correlation and normalized RMS, for both the common core and the surrounding pattern. This is dependent descriptive evidence: seven references reuse seven observations, and each of 21 unordered observation pairs is recorded in both directions. It supplies no calibrated origin probability, physical linewidth, identified line or qualified laser candidate. All seven current labels remain U.

The one frozen run completed on 2026-11-03 at 17:55:28 UTC, after the exact public method readback at commit `514cece459dc1feefafbd2a6faef3958f00ce325` and root release. It retained 42 profile slots, 252 comparison records, 28 identical-product self rows, 21 bounded source windows and all 14 original event/order raw pairs. Fourteen native order-2 profiles are raw-only; zero sources are blocked or excluded. Of the fixed 252 records, 238 raw Pearson values and 224 normalized RMS values are evaluable. The 87 numerical ledger files include 77 NPZ files totaling 780,814 bytes. The frozen method, original outputs and labels have not been changed.

## Merged pattern, seven references and retained variation

The following ranges include all 42 directed nonself records per frame/region, including reciprocal duplicates; medians are descriptive summaries of those shared observations.

| Region / frame | Pearson min | Pearson median | Pearson max | RMS min | RMS median | RMS max |
|---|---:|---:|---:|---:|---:|---:|
| Common core / barycentric | 0.988811 | 0.994096 | 0.995918 | 0.063754 | 0.081471 | 0.118421 |
| Common core / topocentric | -0.528879 | 0.334249 | 0.987756 | 0.111118 | 1.002671 | 1.530699 |
| Surroundings / barycentric | 0.908230 | 0.989986 | 0.992235 | 0.080872 | 0.095837 | 0.297038 |
| Surroundings / topocentric | -0.083633 | 0.043429 | 0.984144 | 0.118047 | 0.906891 | 0.974532 |

Every fixed reference retains all six other epochs. Their median raw Pearson values are shown separately; full six-row statistics and RMS values remain in [the analysis report](../analysis/RESULTS_REPORT.md) and [comparison ledger](../analysis/results/COMPARISONS.json).

| Discovery reference | Core B median r | Core T median r | Surrounding B median r | Surrounding T median r |
|---|---:|---:|---:|---:|
| 0114 / 2022-01-21 | 0.994270 | 0.483437 | 0.989954 | 0.121803 |
| 0119 / 2022-02-05 | 0.994582 | 0.356646 | 0.989522 | 0.033364 |
| 0124 / 2022-05-05 | 0.994242 | 0.417136 | 0.989776 | 0.007513 |
| 0128 / 2023-01-16 | 0.994111 | 0.411928 | 0.990504 | 0.136123 |
| 0133 / 2023-03-22 | 0.994465 | 0.191660 | 0.991325 | 0.069343 |
| 0134 / 2023-05-15 | 0.994045 | 0.365468 | 0.989385 | -0.058449 |
| 0138 / 2023-07-01 | 0.989818 | -0.221500 | 0.910967 | 0.070815 |

The merged figures show an aligned multi-sample central crest and a broader sequence of neighboring peaks/troughs in the barycentric frame. The fixed topocentric window changes that pattern and can include neighbors when the predicted coherent center lies outside its core. It is not empty of similar structure: January 21 2022 versus January 16 2023 has topocentric r 0.987756 in the core and 0.984144 in the surroundings, with RMS 0.111118 and 0.118047 respectively. February 5 2022 versus May 15 2023 also has topocentric core r 0.830024, despite the metadata displacement; these local pattern similarities are retained. Barycentric comparisons still favor both metrics for every directed pair. No favorable-reference subset or binary frame-origin rule is applied.

July 1 2023 retains the lowest barycentric per-reference median agreement, especially in the surroundings, and the fixed broad figures retain a large positive excursion near the outer positive edge in both merged and same-exposure order 3. Its surrounding barycentric pairwise correlations extend down to 0.908230 and RMS up to 0.297038. This visible variation is kept at full scale; no point or epoch is clipped, relabeled or used for a new fitted model. Correlation of the neighboring pattern is part of the context and cannot isolate the catalog center's physical origin.

## Native coverage, signed samples and unavailable scales

All 14 merged and 14 native order-3 frame profiles have 601 finite raw and normalized grid samples, valid positive pooled flank references, false low-reference flags and no nonpositive original samples within the fixed source windows or either flank. Every merged source window contains 600 finite original samples, with 150 in each flank. Native order-3 original window/flank counts differ from the 601 interpolated grid: barycentric windows contain 545–549 samples and topocentric windows 545; all needed flanks are retained. Positive finite ERR coverage is zero throughout all 42 profiles, and gap masks are zero. These counts are not formal uncertainties.

All 14 order-2 frame profiles retain `MISSING_RIGHT_FLANK_COVERAGE`: the whole fixed positive reference flank is absent. Their positive available median comes solely from the left flank and is not a valid two-flank reference. The `flank_reference` and `low_flank_reference` fields remain null; all normalized samples and both normalized comparison regions are unavailable. Their 51-sample raw cores meet the support gate, but every surrounding raw sample count is below 440 and its Pearson value remains unavailable. No order is dropped, no alternative flank is borrowed and no invalid normalization is recast as a measured low-reference result.

| Event | Raw grid B/T | Surrounding support B/T | Signed nonpositive source window B/T | Nonpositive left flank B/T |
|---|---|---|---|---|
| 0114 | 406 / 406 | 355 / 355 | 6/453 / 6/453 | 0/165 / 0/165 |
| 0119 | 402 / 406 | 351 / 355 | 3/449 / 3/454 | 0/165 / 0/166 |
| 0124 | 351 / 406 | 300 / 355 | 6/393 / 6/454 | 1/166 / 1/166 |
| 0128 | 406 / 406 | 355 / 355 | 4/454 / 4/453 | 0/165 / 0/165 |
| 0133 | 379 / 406 | 328 / 355 | 0/424 / 0/453 | 0/165 / 0/165 |
| 0134 | 346 / 406 | 295 / 355 | 2/387 / 2/453 | 0/166 / 0/165 |
| 0138 | 330 / 406 | 279 / 355 | 4/370 / 4/453 | 1/166 / 0/165 |

Thus 12 order-2 frame rows contain nonpositive source-window samples; March 22 2023 has zero in both frames. The May 5 2022 left flank has one nonpositive sample out of 166 in each frame, and July 1 2023 has one out of 166 only barycentrically. The absent right flank is unavailable, not a zero measured fraction. All signed samples remain unchanged. Native order-2 raw core correlations range from 0.843185 to 0.938515 barycentrically and 0.889369 to 0.957542 topocentrically; their unavailable normalized RMS is not inferred from those correlations.

Native order 3 closely reproduces its own same-exposure merged extraction: barycentric core r ranges 0.999174–0.999774 and topocentric 0.999114–0.999775. Its scaled comparison remains explicitly frame dependent: core RMS ranges 0.034692–0.074764 barycentrically and 0.056016–0.146885 topocentrically. This is shared extraction, not independent confirmation of registration, origin or physical flux ratios. Native BUNIT is absent and its extracted units remain unspecified, distinct from uncalibrated merged ADU. Fixed structured flank medians are descriptive reference levels rather than proven line-free continua.

## Coordinate and historical limits

The exact catalog floats remain 3869.3349999999996 Å for 0114/0133, 3869.3325 Å for 0119/0124/0134 and 3869.335 Å for 0128/0138. The fixed midpoint is 3869.33375 Å; its ±0.25 Å metric core differs from individual original cores by up to 0.00125 Å at an edge. All original barycentric core intervals and exact markers remain separate inside the ±3 Å context; the common core is not the full union or a measured linewidth. No core expansion, peak fitting, shift, stellar-RV adjustment or recentering was performed.

The first-queue January 21 discovery fixes the common topocentric anchor 3868.9509913064876 Å at BERV 29.658729150824 km/s. The seven observations span 59.073251754930496 km/s. Independent metadata predictions put three common centers inside the fixed topocentric core: January 21 zero, February 5 +0.038425036 and January 16 2023 −0.004519096 Å. Four are outside on its positive side: May 5 2022 +0.550843536, March 22 2023 +0.265740483, May 15 +0.604748102 and July 1 +0.757919727 Å. All seven original discovery markers are separately retained. These are coordinate predictions, not fitted peaks or full finite-feature coverage; header support, core containment and observed quality remain distinct.

All 14 original mapping records remain staged. For every event, order 2 has original global support true, original local and baseline verification false, with later five-window support true separately; order 3 retains true original stages. Later support does not rewrite the original order-2 failures. Six batch03 events retain original U/U/U reviews. **0128 separately retains original primary I, secondary M normalized to I, and adopted baseline I**, followed by the completed unchanged-coordinate wider mapping diagnosis and separate later U/U/current U. The original 21×25 five-array baseline containers, 2,993 and 3,158 bytes, remain distinct from the later wider containers; no new pixel-equality comparison or completed diagnostic is replayed.

I inspected all ten exact frozen PNGs at original resolution: two merged figures, four native pages and four original raw/excess pages. The order-3 raw contexts show extended central positive patches on a vertical trace-like band with retained edge structure. Order 2 is noisier. The remote high-left deposit in 0134 order 2 dominates its full color scale and leaves the central feature faint; it does not classify the central feature. The smaller original 0128 crops remain visibly separate from the batch03 31×33 panels. These are descriptive visual observations at unchanged full scales, without new pixel statistics, subtraction, crop or contrast variants.

The original epoch/profile/raw evidence and wider 0128 mapping study already existed. Numeric overlaps with C015 and older blue windows use other targets and share no observing products or pixels. This diagnostic adds no observing time, archive completeness or independent evidence, and does not identify a natural or technological origin. The independent actual reconstruction passes 1,268 checks over 161,625 scalar values, preserving every partial outcome and the staged history; source metrics agree exactly. Reproduction agreement validates the fixed arithmetic, not an origin conclusion.

## Next fixed original-queue route

The pre-value handoff remains [C019/R020](NEXT_STEP.md), first unfinished original row 34 with all five members 0115/0120/0125/0129/0135 at rows 34/39/43/47/52. Its exact midpoint is 3881.6137500000004 Å and own January anchor 3881.2297765555622 Å; it reuses these seven HD114783 observations with five discovery references. Thirty directed nonself rows per frame/region would represent 20 unordered pairs plus 10 reciprocal duplicates. Its bounded spectral window is disjoint from C018, while observing-product dependence remains explicit.

All five C019 original reviews remain U/U/U and original orders 3/4 have global/local/baseline support true. Four batch03 events explicitly record later five-window support true; the older 0129 source has no such later field and was not selected in the completed mapping follow-up, so its two later fields remain null/unassessed. The separate 0128 history and failed order-2 stages are not transferred to 0129. Completed normalization routes C013/0092 and C014/0104 and the completed 0128 mapping diagnosis remain skipped. No C019 values were read or executed here. Rubin minimum-50 infrastructure is unchanged; no qualified candidate or calibrated null was created.

The exact numerical ledger is [OUTPUT_HASHES.json](../analysis/results/OUTPUT_HASHES.json), SHA256 `02d21a3bc3fc11752cc7b7a4f7f76578bb45b675f527d6c54178ad681f7b0c7c`. The [plot index](../analysis/results/PLOT_INDEX.json), [independent actual audit](../independent_audit/NUMERICAL_AUDIT.json), [pre-array review](PRE_ARRAY_SCIENTIFIC_REVIEW.json) and [final method review](FINAL_METHOD_REVIEW.json) retain the fixed evidence and limits.
