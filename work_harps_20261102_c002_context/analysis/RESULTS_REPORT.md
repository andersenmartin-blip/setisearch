# C002: HD106515A individual spectral context

The central crest, nearby shoulder and surrounding structured spectrum recur closely in barycentric coordinates across all seven existing target epochs. Native order 3 follows its same-exposure merged spectrum closely. Order 2 is noisier and lacks the entire positive reference flank; its signed raw context is retained with the resulting unavailable statistics. **V2E2-0033 remains U.** This is descriptive context, not a line identification, physical-origin assignment, qualified laser candidate or calibrated null.

The single released execution completed on **2026-11-02 at 19:00:12 UTC**. It retains **18 profile slots and 36 comparisons**, including **four identical-product self-comparisons**, nine bounded source windows and both historical raw panels. No source profile is blocked or structurally excluded. The two order 2 frame profiles are raw-only: **34 raw Pearson values and 32 normalized RMS values are evaluable out of 36 slots each**. Unavailable outcomes remain explicit. The only fixed discovery reference is the observation on 2022-05-07; no new acquisition or observing time was added.

## One fixed reference and all seven epochs

The barycentric air-wavelength center is **3868.6025 Å**. The fixed topocentric anchor is **3868.846286702511 Å**, using the **May 2022 discovery BERV −18.8907517532076 km/s**. The original ±0.25 Å core has **51 grid centers**, with **550 surrounding centers** across the full ±3 Å window on a 0.01 Å grid. Minimum common support is 41 core and 440 surrounding samples. No width, center, lag, stellar velocity, drift, continuum or background was fitted.

Every nonself merged epoch is compared with that unchanged discovery reference below. Values separated by `/` are barycentric/topocentric. Four discovery self rows remain in the complete output at r = 1 to floating-point precision and normalized RMS = 0; they do not add independent evidence.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2022-01-05 | 0.938800 / 0.533582 | 0.965643 / -0.196845 | 0.237223 / 0.848985 | 0.209344 / 1.139846 |
| 2022-03-07 | 0.980641 / -0.131939 | 0.986064 / 0.142508 | 0.160277 / 1.146790 | 0.156301 / 0.974828 |
| 2022-12-31 | 0.957638 / 0.559801 | 0.957488 / -0.164826 | 0.324748 / 0.706058 | 0.337123 / 1.071379 |
| 2023-03-22 | 0.974877 / -0.166783 | 0.985782 / 0.111519 | 0.179102 / 0.850223 | 0.161810 / 1.043705 |
| 2023-05-24 | 0.973546 / 0.036147 | 0.982506 / 0.282579 | 0.137251 / 0.807010 | 0.148133 / 0.922806 |
| 2023-07-03 | 0.959420 / -0.173859 | 0.981869 / -0.098855 | 0.172321 / 0.874266 | 0.150706 / 1.116487 |

Nonself barycentric core r spans **0.938800–0.980641**, with median **0.966483**. Surrounding r spans **0.957488–0.986064**, with median **0.982187**. All six nonself epoch pairs have higher barycentric r and lower barycentric normalized RMS in both regions. This describes the fixed windows, not a calibrated physical-origin test. The core figure retains a multi-sample central crest and a neighboring shoulder near −0.15 Å. The wider spectrum contains repeated peaks and troughs throughout the window; no isolated-feature or physical-linewidth inference follows.

- [All seven epochs: broad signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: fixed original core](results/figures/MERGED_CORE_CONTEXT.png)

Both figures retain their full titles and seven-epoch legends, with matching scales across frames. The marker identifies 0033 / R002 at its catalog/discovery coordinate. It does not follow fitted peaks in other epochs.

## Coordinate displacement in the fixed topocentric core

**The topocentric core is not recentered on the other epochs.** The following positions were calculated from metadata before the observed values were read, assuming a barycentrically coherent center. They are predicted coordinates, not measured peak locations.

| Observation (UTC) | Role | Predicted center offset (Å) | Fixed ±0.25 Å core |
|---|---|---:|---|
| 2022-01-05 | Other epoch | -0.632656925 | Outside |
| 2022-03-07 | Other epoch | -0.382781111 | Outside |
| 2022-05-07 | Discovery | +0.000000000 | Inside |
| 2022-12-31 | Other epoch | -0.635714951 | Outside |
| 2023-03-22 | Other epoch | -0.285919943 | Outside |
| 2023-05-24 | Other epoch | +0.071201260 | Inside |
| 2023-07-03 | Other epoch | +0.133503190 | Inside |

Four predicted centers lie outside the fixed core: January and March 2022, December 2022 and March 2023. The largest displacement is about **0.635715 Å**. The May 2022 discovery, May 2023 and July 2023 centers remain inside. Displaced comparisons may sample neighboring spectral structure in the anchor window. The 59.6098131157401 km/s BERV span supplies coordinate separation, not a calibrated origin discriminator. No alternate anchor or shifted comparison was tried. [All prospective coordinates and assumptions](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Valid references and retained signed samples

The **14 merged profiles and two native order 3 profiles** have complete 601-point raw and normalized support and positive valid flank references. Their **16 low-reference flags are false**. The two order 2 profiles have no valid reference and **low-reference flags are null**, not false. All **18 profiles have zero finite positive ERR samples**.

Merged reference levels range from **143.873 to 300.631 ADU**. Their descriptive first-difference proxies range from **20.297 to 29.568 ADU**. The low-reference rule is reference ≤ 3 × proxy only for a valid reference. It is not formal SNR, and the first-difference proxy is not a formal uncertainty estimate.

Three merged profile rows retain a nonpositive source sample:

| Observation (UTC) | Frame | Nonpositive source samples in window | Nonpositive source samples in left flank |
|---|---|---:|---:|
| 2022-12-31 | barycentric | 1 / 600 (0.1667%) | 1 / 150 (0.6667%) |
| 2023-07-03 | barycentric | 1 / 600 (0.1667%) | 1 / 150 (0.6667%) |
| 2023-07-03 | topocentric | 1 / 600 (0.1667%) | 1 / 150 (0.6667%) |

These three rows concern two observations; the July frame rows are not independent evidence. Their right-flank nonpositive fractions are zero. The other 11 merged profiles and both order 3 profiles have zero nonpositive window fractions. Signed values remain unchanged, and the valid pooled medians remain positive. No clipping, sign change or alternate reference was used.

## Both native orders, including order 2 limitations

Fresh checks of all **72 native order headers** identify orders 2 and 3 as covering the original center. They are two extractions from one discovery observation. Native BUNIT is absent, so their values retain **unspecified extracted units**, distinct from merged ADU. Same-exposure native/merged agreement is not independent confirmation or a physical flux ratio.

Order 2's positive endpoint is only **+1.160941197 Å barycentric / +1.161014356 Å topocentric** from the fixed center. Both frame profiles contain **417 of 601 raw grid samples**, including all **51 core samples** and only **366 of 550 surrounding samples**. The entire positive reference flank [1.5, 3] Å is absent. Its two raw-only reasons are exactly `MISSING_RIGHT_FLANK_COVERAGE`.

Order 2 has **165 finite original samples in the negative flank and zero in the positive flank**. The available one-sided median is **50.288151**, with descriptive first-difference proxy **16.722303**, in unspecified native units in both frames. That available positive median is **not a valid two-flank reference**; `flank_reference` and the low flag remain null. The missing flank, not a measured nonpositive pooled reference, blocks normalization. The historical phrase about low-continuum order 2 context does not replace this current gate result.

In each order 2 frame window, **19 of 465 finite original source samples are nonpositive (4.0860%)**; in its available left flank, **3 of 165 are nonpositive (1.8182%)**. These original-sample counts differ from interpolated-grid support counts. All signed samples and their noisy variation remain visible. Adequate raw core support permits its core Pearson, while 366 surrounding samples fall below the fixed 440-sample minimum. Both surrounding Pearson values and all four order 2 normalized RMS values therefore remain unavailable.

Order 3 has complete 601-point support in both frames. Both reference levels are **157.091766**, and both first-difference proxies are **22.275848** in unspecified native units. Its nonpositive fractions are zero and both valid low flags are false.

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2 | 0.769809 / 0.769773 | Unavailable / Unavailable | Unavailable / Unavailable | Unavailable / Unavailable |
| 3 | 0.998692 / 0.998693 | 0.990287 / 0.990297 | 0.037713 / 0.037715 | 0.112303 / 0.112245 |

[Both native order contexts](results/figures/NATIVE_ORDERS_1.png) retain the full signed order 2 profile and its abrupt coverage end. In its scaled panels, the grey merged spectrum remains visible while the native normalized curve is unavailable and explicitly annotated; it is not a zero-flux native curve. Order 3 follows the merged profile closely with small retained differences across the wider window. No missing order 2 flank or normalized value was filled from order 3.

## Earlier window overlap and structured flanks

The original C002 core [3868.3525, 3868.8525] Å **was already visible in C003's surrounding spectrum**, at offsets [−1.39875, −0.89875] Å from the C003 midpoint. It lies between C003's negative reference flank and original core, outside both masks. The full C002 window [3865.6025, 3871.6025] Å overlaps C003 over [3866.75125, 3871.6025] Å, a width of **4.85125 Å**. It overlaps C004 over [3869.245, 3871.6025] Å, a width of **2.3575 Å**, although the original C002 core lies outside C004's window.

C003's original core union [3869.495, 3870.0075] Å lies inside C002's surrounding region at offsets **+0.8925 to +1.405 Å**. It ends **0.095 Å before** the C002 positive reference flank; it is not inside that flank. Portions of both C002 reference flanks were already visible within C003's wider context. All neighboring structure remains unchanged. The fixed 1.5–3 Å pooled medians are reference levels, not established line-free continua. Positive scalar normalization leaves Pearson unchanged; scaled heights and RMS depend on those reference levels.

Original queue selection preceded C004 interpretation, but C002 flux was already seen in C003 and all seven observations are reused. These results are neither blind nor independent wavelength validation and add no observing time.

## Historical raw panels and mapping qualifications

[Both exact stored raw cutout/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain the noisy order 2 central context and the full order 3 panel. **The order 3 full-value scale is dominated by a separate bright compact patch toward the lower right**, away from the nominal central context. Its central enhancement is subdued at that scale. This separation was already recorded by the historical secondary review as a separate off-event pixel retained for context; the primary/adopted short description concerns the smoother central enhancement. The bright remote patch is not newly assigned to the catalog feature, and no physical origin is assigned to it or to the central structure. The full scales and historical subtraction remain unchanged; no new pixel statistics, registration, background fitting or detector model was applied.

**Order 2 retains historical `local_mapping_usable=false` and `baseline_mapping_verified=false`**, alongside true global and later five-window diagnostics. Order 3's historical stages are true. The later supported mapping diagnostic does not erase the earlier local/baseline failures. Fresh wavelength coverage, core Pearson and order 3 agreement cannot retroactively validate order 2's raw-detector mapping. All primary, secondary and adopted reviews remain preserved in the [input inventory](../inputs/INPUT_INVENTORY.json).

The catalog fixed-template width is not a measured physical linewidth. Missing positive ERR support, reference diagnostics and morphology alone do not establish significance, false-alarm probability, sensitivity or a qualified survey null. The U label and all earlier pipelines remain unchanged.

## Reconstruction and delivery checks

The [independent arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **456 checks across 71,071 scalar values**, covering all nine bounded source windows, 18 profiles, 36 comparisons, two raw copies and four self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Wavelength differences are at most 4.55×10⁻¹³ Å, so wavelength arrays are not bitwise exact. Maximum raw interpolation difference is 3.00×10⁻⁹ native units, normalized-profile difference 1.91×10⁻¹¹ and comparison difference 2.82×10⁻¹⁴. The order 2 missing-flank cause and unavailable comparisons were independently reconstructed.

The exact method was public and read back before execution in commit `264a6d5cfd8b0b40780df1f28b65986f50659b2e`. The [plan](PLAN.json), [release](ROOT_RELEASE.json), [run summary](results/SUMMARY.json), [bounded input index](results/BOUNDED_INPUT_INDEX.json), [complete profile metrics](results/PROFILE_METRICS.json), [complete comparisons](results/COMPARISONS.json) and [output hashes](results/OUTPUT_HASHES.json) bind the calculation.

All four figures were visually inspected, including the full core title and seven-epoch legend at original resolution, the order 2 raw-only annotation and the complete raw panels. PNG decoding, byte sizes and hashes match the unchanged [plot index](results/PLOT_INDEX.json). All **41 frozen method/input sources and 39 numerical output files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records these checks. The next original-queue group is C008; its distinct wavelength region still reuses the same observations and existing historical evidence.
