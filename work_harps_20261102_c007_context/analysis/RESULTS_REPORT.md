# C007: HD106515A individual spectral context

The broad central crest and surrounding structured spectrum recur closely in barycentric coordinates across all seven existing target epochs. The native order 19 extraction also closely follows its same-exposure merged product. **V2E2-0026 remains U.** This is descriptive context, not a line identification, physical-origin assignment, qualified laser candidate or calibrated null.

The single released execution completed on **2026-11-02 at 17:56:14 UTC**, producing **16 profiles and 32 comparisons**, including four explicitly labelled identical-product self-comparisons. All slots are measured; no source is blocked, raw-only or structurally excluded. One discovery reference is fixed: the observation on 2022-01-05. No archive acquisition or new telescope observation was added.

## Fixed reference, all epochs and frame limits

The barycentric air-wavelength center is **4312.700 Å**, with fixed discovery topocentric anchor **4312.266489291718 Å**. The original ±0.25 Å core contains **51 grid centers**; the surrounding region contains **550**. The full window spans ±3 Å on a 0.01 Å grid. Minimum common support is 41 core or 440 surrounding samples. No center, width, lag, stellar velocity, drift, background or continuum was fitted.

The table reports every nonself merged epoch against the unchanged discovery reference. Values separated by `/` are barycentric/topocentric. The four discovery self rows, retained in the complete output, have r = 1 and normalized RMS = 0; they do not add independent evidence.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2022-03-07 | 0.969939 / -0.459282 | 0.987315 / -0.050485 | 0.112839 / 0.812706 | 0.108415 / 0.936304 |
| 2022-05-07 | 0.969837 / -0.385471 | 0.986049 / 0.353807 | 0.115623 / 0.720050 | 0.116348 / 0.715611 |
| 2022-12-31 | 0.959862 / 0.977230 | 0.983498 / 0.990867 | 0.132247 / 0.101542 | 0.125172 / 0.097814 |
| 2023-03-22 | 0.965572 / 0.110665 | 0.985724 / -0.120875 | 0.122898 / 0.641620 | 0.117351 / 0.955748 |
| 2023-05-24 | 0.963341 / -0.013743 | 0.984438 / 0.233288 | 0.130795 / 0.629038 | 0.124143 / 0.768696 |
| 2023-07-03 | 0.966101 / -0.115023 | 0.983174 / 0.016396 | 0.124491 / 0.623550 | 0.128299 / 0.854083 |

Nonself barycentric core r spans **0.959862–0.969939**, with median **0.965836**. Surrounding r spans **0.983174–0.987315**, with median **0.985081**. The figures retain the multi-sample central crest, adjacent troughs and the more extensive pattern of peaks and plateaus. The discovery profile differs slightly from the other epochs in the core; no fitted shift or width is used to improve that agreement.

The 2022-12-31 epoch is the explicit near-BERV exception: its core r is **0.959862 B versus 0.977230 T**, and surrounding r is **0.983498 B versus 0.990867 T**. Its BERV differs from discovery by about 0.237 km/s, despite the nearly year-long time separation. There is no universal pairwise frame ranking. The full seven-epoch BERV span of 59.6098131157401 km/s is coordinate separation, not a calibrated origin test.

**The fixed topocentric core is not recentered on each later feature.** Metadata predicts that a barycentrically coherent center lies outside its ±0.25 Å core in five of the seven epochs: March and May 2022, then March, May and July 2023. The largest predicted offset is 0.854112 Å. Only discovery and December 2022 retain that center inside the fixed core. These are coordinate predictions, not fitted peaks; those displaced comparisons may sample neighboring spectral structure. [All prospective offsets](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

All **16 profiles** have full 601-point raw and normalized support, positive references, false low-reference flags, zero nonpositive source-window fractions and **zero finite positive ERR samples**. Merged reference levels span **953.534–2730.263 ADU**, with descriptive first-difference proxies **70.424–200.000 ADU**. These proxies and flags are not formal uncertainties or SNRs.

- [All seven epochs: broad signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: fixed original core](results/figures/MERGED_CORE_CONTEXT.png)

The marker identifies V2E2-0026 / R008 at the catalog/discovery coordinate; it does not track fitted peaks in the other epochs. Both figures retain the full title, seven-epoch legend and matching frame scales.

## Prior overlap and structured reference flanks

The C007 core **was already visible in C006's positive normalization flank**. The current barycentric window [4309.700, 4315.700] Å intersects C006's window over [4309.700, 4313.455] Å, a continuous width of 3.755 Å. The same seven observing products are reused. The original queue fixed this C007 continuation before C006 results, but subsequent flux interpretation is not blind or independent; neither the overlap nor the same exposures add independent observing time or detections.

The dependence is reciprocal: the C006 catalog centers 4310.305–4310.605 Å lie at C007 offsets −2.395 through −2.095 Å, and their complete original core union lies inside C007's negative normalization flank. Those known structures remain in the fixed median without masks or alternative flanks. Both 1.5–3 Å flanks contain spectral structure and are **reference levels, not line-free continua**. Positive scalar division leaves Pearson unchanged, while heights and normalized RMS depend on the chosen fixed reference levels.

## Native extraction and preserved raw evidence

Fresh header checks of all 72 native orders identify only order 19 as covering the original feature center. Both native frame profiles have full support. Native BUNIT is absent, so native values retain **unspecified extracted units**, distinct from merged ADU. Both native references are **1848.422**, with first-difference proxy **170.853** in those units; both nonpositive fractions are zero and both low flags are false.

| Discovery native context | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| V2E2-0026 / order 19 | 0.999890 / 0.999890 | 0.998920 / 0.998924 | 0.007513 / 0.007486 | 0.037867 / 0.037753 |

[The native and same-exposure merged profiles](results/figures/NATIVE_ORDERS_1.png) follow one another closely throughout the window. Small normalized differences remain visible, including on the positive-flank plateaus. Shared extraction lineage means these comparisons are not independent confirmations or physical flux ratios.

[The exact stored raw cutout/excess pair](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retains a diffuse central enhancement together with much stronger right-edge structures. The existing raw-excess map retains alternating positive and negative edge lobes under full panel scales. No detector-origin assignment is made to the central or edge structures. The historical subtraction is preserved; no new registration, background fit, detector model or pixel statistics were applied.

**0026 retains historical `local_mapping_usable=false` and `baseline_mapping_verified=false`**, alongside true global and later five-window diagnostics. Fresh coordinate coverage and close native/merged agreement do not retroactively validate that local raw-detector mapping. All primary, secondary and adopted reviews remain preserved. The original fixed-template width is not a measured physical linewidth. Missing positive ERR support and descriptive noise proxies do not establish significance, false-alarm probability, sensitivity or a survey null. The U label remains unchanged.

## Reconstruction and delivery checks

The [independent arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **410 checks across 64,179 scalar values**, covering all eight source windows, 16 profiles, 32 comparisons and the exact raw copy without importing production functions. Source flux, ERR and indices agree exactly. Wavelength differences are at most 9.09×10⁻¹³ Å; they are not bitwise exact. Maximum raw-profile interpolation difference is 4.38×10⁻⁸ native units, normalized-profile difference 2.37×10⁻¹¹ and comparison difference 9.51×10⁻¹⁴.

The exact method was public and read back before execution in commit `57b5af70c88a3a4ee5fe8f9224ac805a7c3c438a`. The [plan](PLAN.json), [release](ROOT_RELEASE.json), [run summary](results/SUMMARY.json), [bounded input index](results/BOUNDED_INPUT_INDEX.json), [complete profile metrics](results/PROFILE_METRICS.json), [complete comparisons](results/COMPARISONS.json) and [output hashes](results/OUTPUT_HASHES.json) bind the calculation.

All four figures were visually inspected, including the core title and legend at original resolution. Their complete PNG decoding, byte sizes and hashes match the unchanged [plot index](results/PLOT_INDEX.json). All 39 frozen method/input sources and 35 numerical output files remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records those checks. The next original-queue group is C004; its predeclared overlap with earlier C003 context must remain explicit.
