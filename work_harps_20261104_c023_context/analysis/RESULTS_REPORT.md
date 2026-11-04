# C023 / HD114783 at 5944.965 air Angstrom

**Complete: seven existing observations, one own February 5 discovery reference, sixteen profiles and thirty-two comparisons. V2E2-0122 remains U.**

The central core and surrounding spectrum have different descriptive frame behavior. All six other epochs have better surrounding-spectrum raw correlation and normalized RMS in the barycentric frame. In the original core, raw correlation is higher topocentrically in five of six comparisons, while normalized RMS is lower topocentrically in four of six. These uncalibrated statistics do not assign origin, identify a physical line, qualify a laser candidate or calibrate significance, sensitivity or a survey null.

## Fixed scope and all nonself comparisons

The exact original center is 5944.965 Å, core [5944.715,5945.215] Å and broad window [5941.965,5947.965] Å. The unchanged 0.01-Angstrom grid has 51 core and 550 surrounding points. Own discovery ADP.2022-02-06T01:07:28.382 was observed on 2022-02-05 at BERV 26.6810328154809 km/s and fixes topocentric anchor 5944.43595503388 Å. No center, width, lag, stellar velocity, drift, continuum, background or mask was fitted.

Each cell below is **barycentric / topocentric**. Six rows represent six other observations against one fixed reference; the cohort contains seven observations. Four identical-product self-comparison records remain labelled and add no recurrence evidence.

| Other observation | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2022-01-21 | 0.120163 / 0.619864 | 0.771903 / 0.671854 | 0.035950 / 0.026314 | 0.036860 / 0.042938 |
| 2022-05-05 | 0.090385 / 0.345971 | 0.838155 / 0.057040 | 0.029741 / 0.038927 | 0.023385 / 0.081955 |
| 2023-01-16 | 0.165415 / 0.629223 | 0.856137 / 0.612750 | 0.029461 / 0.023740 | 0.024004 / 0.039085 |
| 2023-03-22 | -0.094559 / 0.569345 | 0.672856 / 0.322784 | 0.041392 / 0.051797 | 0.044202 / 0.059236 |
| 2023-05-15 | -0.594879 / 0.539964 | 0.549113 / 0.252422 | 0.041145 / 0.030093 | 0.047994 / 0.083236 |
| 2023-07-01 | 0.383694 / 0.362813 | 0.864782 / 0.099439 | 0.028050 / 0.027652 | 0.021812 / 0.079340 |

[All seven original-core profiles](results/figures/MERGED_CORE_CONTEXT.png) · [Full surrounding spectrum](results/figures/MERGED_BROAD_CONTEXT.png)

The discovery retains a raised, flat-topped or rounded central shape whose scaled appearance differs from all six other epochs. The broader spectrum includes recurring absorption structure that aligns more closely barycentrically. This visual description is not a fitted amplitude, width, repeatability test or a specific identification of the central event. The nearby structure remains inside the fixed windows and references.

May 5 2022 and March 22 2023 illustrate the distinction between shape and scale: their core raw correlation favors the topocentric frame, while normalized RMS favors the barycentric frame. The July comparison has a small barycentric correlation advantage (0.383694 versus 0.362813), but topocentric RMS is lower. Pearson is unchanged by positive scalar normalization; normalized RMS also reflects the retained reference levels and amplitude mismatch. No statistic is selected as an origin verdict.

## Actual finite support and reference quality

All sixteen profiles have 601 finite raw and normalized grid points, valid positive pooled flank medians and false low-reference flags. None is raw-only, partial or blocked. All thirty-two raw Pearson and thirty-two normalized RMS values are evaluable. Every retained original source sample in the fixed windows and flanks is positive; this is a measured outcome, not an inference from geometry. There are zero positive finite ERR samples in every profile. False low-reference flags and first-difference proxies are not formal SNR, significance or general quality certificates.

The discovery merged reference is 26451.701172 ADU, with 150 finite original samples in each flank. Native order 57 has reference 42398.552734 in unspecified native units, with 92/94 finite source samples in the negative/positive flanks and 372 finite original source samples in each fixed window. Native BUNIT is absent; the native and merged divisors are not a physical flux ratio. Structured flank samples remain unchanged without line-free assumptions.

## Own native order and original raw context

A fresh header-only scan of all 72 native orders selects order 57 only. Both fixed frames geometrically cover the full core, ±3 context and reference flanks. Actual finite support is reported above, separately from header geometry. The native product compares only with its own discovery merged extraction:

| Frame | Core raw r | Surrounding raw r | Core normalized RMS | Surrounding normalized RMS |
|---|---:|---:|---:|---:|
| barycentric | 0.998689 | 0.942440 | 0.004984 | 0.014743 |
| topocentric | 0.998689 | 0.942447 | 0.004984 | 0.014742 |

[Native order 57 against its own merged extraction](results/figures/NATIVE_ORDERS_1.png)

The central extracted shape agrees closely within the same exposure, while surrounding structure retains larger differences. Shared extraction is dependent evidence, not another observation or an origin confirmation. Original order-57 global, local, baseline and later reference-support stages are all true. These historical mapping stages do not resolve the original morphology.

[Complete original stored raw/excess pair](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) preserves every saved pixel and separate full scales. At those full scales the central enhancement is faint beside dominant right-edge structure. The historical primary and secondary enlarged-view descriptions retain an irregular/asymmetric multi-row central excess, a bright lower component and an upper-right extension, with a possible charge/photon mixture. Those records remain U/U/U. No new enlargement, contrast variant, crop, subtraction, registration or detector statistic is introduced; right-edge structure does not classify the central feature.

## Fixed-frame geometry and dependence

| Observation | Predicted coherent center offset from fixed topocentric anchor (Å) | Inside fixed ±0.25 core |
|---|---:|---|
| 2022-01-21 | -0.059037423 | yes |
| 2022-02-05 | +0.000000000 | yes |
| 2022-05-05 | +0.787295758 | no |
| 2023-01-16 | -0.065980703 | yes |
| 2023-03-22 | +0.349254540 | no |
| 2023-05-15 | +0.870116414 | no |
| 2023-07-01 | +1.105454074 | no |

Three metadata-predicted coherent centers stay inside the fixed topocentric core and four fall outside. These are predictions under a barycentric-coherence assumption, not fitted peaks or proof of full finite-feature coverage. A fixed topocentric window can sample neighboring structure; frame statistics are descriptive rather than calibrated origin tests.

The same seven January 2022–July 2023 HD114783 observations and the same native product lineage were used previously. This C023 wavelength window is disjoint from completed same-target C017/C018/C019/C021/C022 bounded windows, but observing products are shared and the original 0122 epoch/raw evidence was already exposed. No blind or untouched-data validation, independent new observation or added observing time is claimed.

## Arithmetic, delivery and next action

The method and source-only/synthetic checks were public before observed C023 values. Exact readback covered 23 files at commit `2956edd4e14885ce6fa83041cbd3ead2ffcf4aa2`. The 97 synthetic preflight checks and 1,449 separate scalar checks over 73,016 synthetic values passed before execution.

The separate observed reconstruction passes **437 checks / 63,569 scalar comparisons** across all eight bounded source windows, sixteen profiles, thirty-two comparisons and the byte-exact original raw container. Source flux, ERR and indices agree exactly. Maximum source-wavelength difference is 9.095e-13 Å, raw interpolation difference 9.349e-08 native units, normalized difference 2.205e-12 and comparison difference 5.451e-14. Fixed tolerances pass; floating-point wavelength/interpolation results are not claimed bitwise identical.

All four scientific PNGs were visually inspected and fully decoded; all 47 source bindings and original numerical outputs stayed unchanged. Separate formulas and fresh processes were run by the same assistant, without a separate-agent or human-review claim.

[Fixed plan](PLAN.json) · [Released method](ROOT_RELEASE.json) · [Profile metrics](results/PROFILE_METRICS.csv) · [All comparisons](results/COMPARISONS.csv) · [Output hashes](results/OUTPUT_HASHES.json) · [Scalar audit](../independent_audit/NUMERICAL_AUDIT.json)

**Next:** original queue row 53, C020/R021, V2E2-0136 on HD114783 at 4303.13 Å. Its own May 15 2023 discovery reference and source-specific raw/mapping history are retained in [the next metadata handoff](../scientific_review/NEXT_GROUP_METADATA.json). The selection preceded C023 values; do not inherit the February reference, order-57 scope or quality. Freeze its separate method before any new observed arithmetic. C023 is closed as this fixed diagnostic with U unchanged. Completed mapping, normalization and other profile routes are not replayed. Rubin remains limited feasibility with minimum 50 unmet.
