# C020 / HD114783 at 4303.13 air Angstrom

**Complete: seven existing observations, one own May 15 discovery reference, sixteen profiles and thirty-two comparisons. V2E2-0136 remains U.**

All six other epochs have higher raw correlation and lower normalized RMS in the barycentric frame, in both the original core and surrounding spectrum. A broad central crest, nearby rise and broader multi-peak pattern recur with amplitude differences. This descriptive agreement does not assign physical origin, identify a line, qualify a laser candidate or calibrate significance, sensitivity or a survey null.

## Fixed scope and every nonself comparison

The exact original center is 4303.13 Å, core [4302.88,4303.38] Å and broad context [4300.13,4306.13] Å. The unchanged 0.01 Å grid has 51 core and 550 surrounding points. Own discovery ADP.2023-05-16T01:01:18.574 was observed on 2023-05-15 at BERV −17.1985506565257 km/s and fixes topocentric anchor 4303.376876941822 Å. No center, width, lag, stellar velocity, drift, continuum, background or mask was fitted.

Each cell is **barycentric / topocentric**. Six rows are six other observations against one fixed reference, within a seven-observation cohort. Four identical-product self-comparison records remain explicitly labelled and add no recurrence evidence.

| Other observation | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2022-01-21 | 0.996959 / 0.029030 | 0.998531 / 0.015616 | 0.036984 / 0.841741 | 0.035914 / 0.811092 |
| 2022-02-05 | 0.996359 / -0.134054 | 0.998506 / -0.010084 | 0.040798 / 0.911133 | 0.036647 / 0.825208 |
| 2022-05-05 | 0.996049 / 0.070615 | 0.998373 / 0.627951 | 0.041068 / 0.600365 | 0.035705 / 0.501826 |
| 2023-01-16 | 0.996114 / 0.063808 | 0.998569 / 0.017322 | 0.041052 / 0.829839 | 0.034440 / 0.810262 |
| 2023-03-22 | 0.996788 / -0.358427 | 0.998698 / -0.181631 | 0.035317 / 0.718499 | 0.029630 / 0.898303 |
| 2023-07-01 | 0.995574 / -0.160312 | 0.998018 / 0.115637 | 0.040862 / 0.660174 | 0.037609 / 0.762248 |

[All seven original-core profiles](results/figures/MERGED_CORE_CONTEXT.png) · [Full surrounding spectrum](results/figures/MERGED_BROAD_CONTEXT.png)

The central rounded crest and neighboring rise align closely in the barycentric frame after the fixed scalar normalization. The complete broad window retains many structured peaks and troughs; it is not a flat, isolated-line continuum. Signed raw amplitude differences remain visible. No peak width or amplitude was fitted, and high correlation does not separately identify the central event.

## Actual finite support and reference quality

All sixteen profiles have 601 finite raw and scaled grid points, valid positive pooled flank medians and false low-reference flags. None is partial, raw-only or blocked. All thirty-two raw Pearson and thirty-two normalized RMS values are evaluable. Every retained original source sample in the fixed windows and flanks is positive; this is a measured outcome, separate from header geometry. Every profile has zero positive finite ERR samples. Low-reference and first-difference proxies do not calibrate formal SNR or significance.

The discovery merged reference is 2212.0908203125 ADU in both frames. Its barycentric negative/positive flanks contain 151/151 finite original samples; its topocentric flanks contain 150/150. Original window counts are 601 and 599 respectively. The fixed 601-point interpolated profiles remain fully supported; floating boundary-count differences are retained without changing the windows. Native order 19 has reference 2353.91015625 in unspecified units, 120/123 finite original flank samples and 486 finite original window samples in each frame. Structured flank samples remain without line-free assumptions. These native/merged divisors are not a physical flux ratio.

## Own native order and original raw context

A fresh header-only scan of all 72 native orders selected only order 19. Both frames geometrically cover the full core, context and reference flanks. Finite sample quality was subsequently measured, as reported above. The native product compares only with its own discovery merged extraction:

| Frame | Core raw r | Surrounding raw r | Core normalized RMS | Surrounding normalized RMS |
|---|---:|---:|---:|---:|
| barycentric | 0.999754 | 0.992440 | 0.015162 | 0.074074 |
| topocentric | 0.999754 | 0.992445 | 0.015151 | 0.074032 |

[Native order 19 against its own merged extraction](results/figures/NATIVE_ORDERS_1.png)

Same-exposure extracted shapes agree closely, with larger surrounding differences. This is dependent extraction evidence, not another observation or an origin confirmation. The original global, local, baseline and later mapping-support stages are all true; their support does not classify the broad native feature.

[Complete original stored raw/excess pair](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retains every saved pixel and separate full scales. A faint, diffuse central enhancement sits beside much brighter right-edge structure. The historical primary description retains a broad native peak, nearby secondary rise and weak diffuse raw enhancement. The secondary description retains a broad rounded native feature, neighboring emission-like structure and a smooth raw trace enhancement. Original primary, secondary and adopted codes remain U/U/U. No new crop, contrast variant, subtraction, registration or detector statistic was introduced. Right-edge structure does not classify the central feature.

## Fixed-frame geometry and source-pixel dependence

| Observation | Predicted coherent center offset from fixed topocentric anchor (Å) | Inside fixed ±0.25 core |
|---|---:|---|
| 2022-01-21 | -0.672547231 | no |
| 2022-02-05 | -0.629814312 | no |
| 2022-05-05 | -0.059947880 | yes |
| 2023-01-16 | -0.677572969 | no |
| 2023-03-22 | -0.377014222 | no |
| 2023-05-15 | +0.000000000 | yes |
| 2023-07-01 | +0.170343904 | yes |

3 metadata-predicted coherent centers lie inside the fixed topocentric core and 4 outside. These are predictions under a barycentric-coherence assumption, not fitted peaks or proof of full finite-feature coverage. A fixed topocentric core can sample neighboring structure when that predicted center leaves it; frame statistics remain descriptive.

The nominal C020 and C021 barycentric ±3 Å windows have a 0.69625 Å gap. Their unions of source samples needed for both frames differ because their own reference anchors differ. The frozen source-index audit confirms **17 shared original merged-spectrum samples for the July 1 2023 product**, indices [52377,52394), and zero sharing for the other six products. It verifies the identical full-source SHA for each pair against the preserved C021 index metadata, without reading C021 array values. The overlap was anticipated before current values; no mask or window change follows. No source-pixel independence is claimed.

[Exact source-index dependency audit](../independent_audit/SOURCE_PIXEL_DEPENDENCY_AUDIT.json). The same seven January 2022–July 2023 observations and original 0136 epoch/raw evidence were already exposed. No blind or untouched-data validation, independent new observation or added observing time is claimed.

## Arithmetic, delivery and next unfinished route

The method, source-only review and synthetic checks were public before observed C020 values. Exact readback covered 24 files at commit `f239991e8e36ff5cd2abf7701e67a53badfa5352`. The 111 compact preflight checks and 1,449 separate scalar checks over 73,010 synthetic values passed before execution.

The separate observed reconstruction passes **480 checks / 63,829 scalar comparisons** across all eight bounded input windows, sixteen profiles, thirty-two comparisons, the byte-exact original raw container and the seven source-index dependency pairs. Source flux, ERR and original indices agree exactly. Fixed numerical tolerances pass; wavelength/interpolation arithmetic is not claimed bitwise identical. Maximum absolute differences:

| Quantity | Maximum absolute difference |
|---|---:|
| comparison | 4.80310236028e-14 |
| input_barycentric_wavelength | 9.09494701773e-13 |
| input_metadata | 0 |
| input_signed_source_flux | 0 |
| input_source_error | 0 |
| input_source_indices | 0 |
| input_source_wavelength | 9.09494701773e-13 |
| profile_metric | 0 |
| profile_normalized_flux | 1.09285913652e-11 |
| profile_offset | 0 |
| profile_requested_bary_wave | 0 |
| profile_signed_raw_flux | 2.57250576396e-08 |

All four scientific PNGs were visually inspected and fully decoded. All 61 frozen source bindings and the original numerical outputs stayed unchanged. Separate scalar formulas and fresh processes were run by the same assistant; no independent human or separate-agent review is claimed.

[Fixed plan](PLAN.json) · [Released method](ROOT_RELEASE.json) · [Profile metrics](results/PROFILE_METRICS.csv) · [All comparisons](results/COMPARISONS.csv) · [Output hashes](results/OUTPUT_HASHES.json) · [Scalar audit](../independent_audit/NUMERICAL_AUDIT.json)

**Next unfinished route:** original queue row 62, C028/R029/V2E2-0260 on **HD126093**, exact center **3864.5550000000003 Å**. Use its six April–July 2025 observations and its own April 27 discovery at BERV 5.77068898867443 km/s; the cohort span is 29.26984563734743 km/s. Own raw batch04 history retains orders 2 and 3, original local/baseline failures and later mapping support. Freshly scan all 72 own native headers and freeze a separate fixed diagnostic before new observed arithmetic. No HD114783 seven-epoch count, May reference, order-19 scope, BERV span or quality outcome is transferred.

All exact C001–C023 routes are now complete, including C013/C014 normalization. The ten exact FRAME_BASELINE_CONTEXT records were already completed in the earlier bounded BERV and May-quality work and are skipped with [source-bound proof](../scientific_review/COMPLETED_ROUTE_SKIP_PROOF.json). Their physical U status remains. The four HD135204 records had no new selected epoch under those bounded filters; this is not archive-wide absence. The separate 0235 spatial/background route stays closed. See [the exact next handoff](../NEXT_ACTION.json). No completed diagnostic is replayed solely because U remains. Rubin stays limited feasibility with minimum 50 unmet.
