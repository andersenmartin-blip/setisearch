# C005: HD106515A joint spectral context

The C005 central feature and wider structured spectrum align closely in the barycentric frame across all seven existing cohort epochs and all five discovery references. Both native orders retain the central shape, with order-dependent differences in the surrounding profile. Two order 4 topocentric profiles have low flank references under the predeclared quality flag; those results remain visible. **All five records remain U. No origin or line-width classification is assigned.**

The single released execution completed on **2026-11-02 at 16:33:38 UTC**: **34 profiles, 180 comparisons and 20 identical-product self-comparisons**, with no blocked profiles, raw-only normalization slots or structural exclusions. All ten historical native-order/raw contexts are retained. Scope is the original seven-exposure HD106515A cohort, not archive-wide completeness. C003 used these same exposures at another wavelength; these groups are not independent exposure samples.

## All five references and fixed coordinates

The shared barycentric air-wavelength center is **3882.0375 Å**, with one fixed first-discovery topocentric anchor at **3881.6472792969134 Å**. The ±3 Å window has 601 centers at 0.01 Å spacing. The nominal ±0.2525 Å union core selects 51 centers (−0.25 to +0.25 Å); the surrounding region contains 550. Signed flux is retained. Each profile/frame uses its own positive pooled median from the unchanged 1.5–3 Å flanks, requiring at least 20 finite source samples on each side. No continuum, width, lag, center, stellar velocity or drift was fitted.

The table reports **minimum–maximum across all six nonself epochs for each discovery reference**. B/T means barycentric/topocentric. These are descriptive summaries of the frozen comparisons, not new detection statistics. All 20 self-comparisons remain in the detailed output at r = 1 and RMS = 0. Reversed discovery pairs and reused references share data.

| Reference (observation date) | Region | r B range | r T range | Normalized RMS B range | Normalized RMS T range |
|---|---|---:|---:|---:|---:|
| 0023 (2022-01-05) | Core | 0.912–0.960 | -0.558–0.925 | 0.182–0.496 | 0.472–2.682 |
| 0023 (2022-01-05) | Surroundings | 0.948–0.982 | -0.049–0.950 | 0.124–0.209 | 0.203–1.881 |
| 0029 (2022-03-07) | Core | 0.944–0.994 | -0.711–0.667 | 0.070–0.561 | 0.489–2.550 |
| 0029 (2022-03-07) | Surroundings | 0.963–0.995 | -0.022–0.450 | 0.071–0.177 | 0.866–1.865 |
| 0035 (2022-05-07) | Core | 0.950–0.991 | -0.554–0.791 | 0.069–0.597 | 1.189–2.480 |
| 0035 (2022-05-07) | Surroundings | 0.955–0.991 | 0.010–0.634 | 0.088–0.191 | 1.214–1.760 |
| 0046 (2023-03-22) | Core | 0.945–0.994 | -0.562–0.791 | 0.063–0.594 | 0.854–2.507 |
| 0046 (2023-03-22) | Surroundings | 0.963–0.995 | 0.255–0.450 | 0.071–0.177 | 1.023–1.646 |
| 0054 (2023-07-03) | Core | 0.938–0.990 | -0.556–0.210 | 0.086–0.632 | 1.798–2.682 |
| 0054 (2023-07-03) | Surroundings | 0.949–0.987 | -0.049–0.694 | 0.106–0.202 | 1.139–1.881 |

Nonself barycentric core r spans **0.9121–0.9942**, and surrounding r **0.9476–0.9945**. The plots show a central crest embedded in a repeated wider pattern of peaks, troughs and a raised region near +2 Å. The near-BERV 2022-12-31 epoch against reference 0023 is an explicit exception to a simple frame ranking: core r is **0.9121 B / 0.9248 T**, and surrounding r **0.9476 B / 0.9502 T**.

**The topocentric core is a fixed coordinate window, not each later feature’s recentered core.** Header-derived coordinate conversion places the common feature center outside it for four of seven epochs, including discovery references 0035, 0046 and 0054. Their topocentric core metrics can sample neighboring structure at the anchor. The maximum expected displacement is about 0.7688 Å; this is metadata geometry, not a fitted feature center. The 59.610 km/s BERV span (22.866 nominal resolution elements) does not calibrate an origin test. All references and both frames remain, without choosing a favorable result.

All 14 merged profiles have complete support, usable positive flank references **119.28–544.85 ADU**, descriptive noise proxies **18.42–42.47 ADU**, false low-reference flags and zero nonpositive window samples. Flank medians sample structured spectra, not established quiet continuum.

- [All seven epochs: ±3 Å context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same profiles: fixed core close-up](results/figures/MERGED_CORE_CONTEXT.png)

## Every native-order quality result

Each native order is compared with its own exposure’s merged product. These pairs share extraction lineage and are not independent observations. Native BUNIT is absent, so the levels below have **unspecified native extracted units**; merged flux is explicitly ADU. Cross-order and native/merged scale ratios are not physical flux measurements.

All 20 native profiles have complete 601-point coverage and valid positive references. Values separated by `/` are B/T. Nonpositive fractions refer to finite source-window samples. “Low” is the fixed reference ≤ 3 × first-difference-noise-proxy flag; it does not invalidate an otherwise positive reference.

| Event/order | Reference B/T | Noise proxy B/T | Nonpositive % B/T | Low flag B/T |
|---|---:|---:|---:|---|
| 0023/3 | 281.15 / 280.61 | 26.13 / 26.10 | 0.00 / 0.00 | false / false |
| 0023/4 | 85.33 / 85.33 | 21.56 / 21.56 | 1.39 / 1.39 | false / false |
| 0029/3 | 465.42 / 342.93 | 34.30 / 31.15 | 0.00 / 0.00 | false / false |
| 0029/4 | 139.87 / 95.59 | 20.69 / 19.70 | 0.00 / 1.00 | false / false |
| 0035/3 | 263.45 / 137.92 | 26.04 / 23.07 | 0.00 / 0.00 | false / false |
| 0035/4 | 97.48 / 40.55 | 19.06 / 16.20 | 1.79 / 2.99 | false / true |
| 0046/3 | 446.57 / 276.08 | 33.23 / 25.95 | 0.00 / 0.00 | false / false |
| 0046/4 | 131.99 / 83.92 | 20.41 / 18.34 | 0.20 / 1.39 | false / false |
| 0054/3 | 239.59 / 108.89 | 23.76 / 18.05 | 0.00 / 0.00 | false / false |
| 0054/4 | 79.19 / 32.03 | 20.38 / 16.20 | 1.78 / 4.98 | false / true |

The two true low-reference flags are **0035/order 4 topocentric** (40.55 versus noise 16.20; ratio about 2.50) and **0054/order 4 topocentric** (32.03 versus 16.20; ratio about 1.98). Their corresponding barycentric ratios are about 5.11 and 3.89, with false flags. They are not hidden or removed: both frames remain evaluable under the frozen positive-reference rule. Their topocentric nonpositive fractions are 2.99% and 4.98%, respectively.

**Frame-dependent flank scaling can enlarge plotted heights and normalized RMS**, particularly in those two profiles. It does not establish physical brightening. Pearson correlation is invariant to positive scalar division, so high core r can coexist with a low reference and a larger normalized mismatch. No alternative normalization was selected.

| Event/order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 0023/3 | 0.9957 / 0.9957 | 0.9631 / 0.9631 | 0.0596 / 0.0603 | 0.1856 / 0.1850 |
| 0023/4 | 0.9791 / 0.9791 | 0.8909 / 0.8910 | 0.1669 / 0.1669 | 0.5078 / 0.5077 |
| 0029/3 | 0.9973 / 0.9969 | 0.9616 / 0.9675 | 0.0836 / 0.0827 | 0.2213 / 0.2035 |
| 0029/4 | 0.9917 / 0.9888 | 0.8861 / 0.8960 | 0.0921 / 0.2128 | 0.4935 / 0.8078 |
| 0035/3 | 0.9953 / 0.9956 | 0.9530 / 0.9653 | 0.0662 / 0.2172 | 0.2077 / 0.5082 |
| 0035/4 | 0.9820 / 0.9787 | 0.8782 / 0.9058 | 0.1094 / 0.4455 | 0.4363 / 0.9660 |
| 0046/3 | 0.9972 / 0.9939 | 0.9587 / 0.9684 | 0.0461 / 0.1275 | 0.1881 / 0.2605 |
| 0046/4 | 0.9911 / 0.9717 | 0.8812 / 0.8975 | 0.1234 / 0.2270 | 0.5875 / 0.8055 |
| 0054/3 | 0.9933 / 0.9933 | 0.9459 / 0.9650 | 0.1078 / 0.2256 | 0.2227 / 0.5095 |
| 0054/4 | 0.9778 / 0.9653 | 0.8662 / 0.9028 | 0.1598 / 0.7652 | 0.5306 / 1.0035 |

Across both frames, same-exposure native order 3 core r is **0.9933–0.9973**, while surrounding r is **0.9459–0.9684**. Order 4 core r is **0.9653–0.9917**, while surrounding r is **0.8662–0.9058**. The central shapes agree more closely than the whole surrounding profile. Near the broad +2 Å raised region, order 3 lies below and order 4 above the merged curve after each profile’s own flank scaling. These persistent level/shape differences must not be described as perfect agreement or attributed solely to noise; their cause is not fitted here. The same fixed-anchor caveat applies to later-reference topocentric core pairs.

- [Native page 1: 0023 and 0029](results/figures/NATIVE_ORDERS_1.png)
- [Native page 2: 0035 and 0046](results/figures/NATIVE_ORDERS_2.png): **0035/order 4 topocentric has a low reference**; its taller scaled profile and RMS require that context.
- [Native page 3: 0054](results/figures/NATIVE_ORDERS_3.png): **0054/order 4 topocentric has a low reference**; scaling amplifies the displayed relative height. The figure remains unchanged.

## Preserved raw context and limitations

All ten historical cutouts and stored excess maps remain exact. Multi-pixel enhancements near the central trace are visible in both orders, with lower contrast in several order 4 panels. Separate compact off-center or edge spots in **0023/order 4, 0029/order 4 and 0054/order 3** dominate their full-value color scales; they must not be conflated with the central enhancement. The noisier 0054/order 4 context and distinct historical primary, secondary and adopted review records remain preserved. No clean photon-only or charge-origin conclusion follows.

- [Raw page 1: 0023 and 0029](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png)
- [Raw page 2: 0035 and 0046](results/figures/PRESERVED_RAW_ORDER_CONTEXT_2.png)
- [Raw page 3: 0054](results/figures/PRESERVED_RAW_ORDER_CONTEXT_3.png)

The raw-excess subtraction is historical and panel scales are separate. No new registration, background fit, detector statistic or morphology classifier was applied. All **34 profiles have zero finite positive ERR samples**. The descriptive noise proxy provides no formal uncertainty or significance. Five overlapping records, reused epochs and same-exposure native/merged pairs do not become independent detections through these comparison counts. No physical flux, free-width estimate, false-alarm rate or completeness is inferred; all historical pipelines and labels remain unchanged.

## Reproduction and presentation QA

The [independent numerical audit](../independent_audit/NUMERICAL_AUDIT.json) passed **895 checks across 135,577 scalar values**, reconstructing all 17 bounded inputs, 34 profiles, 180 comparisons and ten raw copies without importing production functions. Source flux/error/index values were exact; maximum normalized-profile difference was 2.15×10⁻¹¹ and maximum comparison difference 1.86×10⁻¹³. All 54 bound sources and numerical outputs were preserved.

The method was published before execution at commit `b9e06d67e3a499dd93bf1b718820a18b0ddbe395`. [PLAN.json](PLAN.json), [ROOT_RELEASE.json](ROOT_RELEASE.json), [SUMMARY.json](results/SUMMARY.json) and [OUTPUT_HASHES.json](results/OUTPUT_HASHES.json) bind the run. [BOUNDED_INPUT_INDEX.json](results/BOUNDED_INPUT_INDEX.json) identifies compact pre-interpolation coordinates, signed flux, available errors and original indices. [PROFILE_METRICS.json](results/PROFILE_METRICS.json) and [COMPARISONS.json](results/COMPARISONS.json) retain every detailed value and support count.

All eight delivered images were visually inspected, including the complete saved core title and seven-epoch legend. One raw page 2 file was found truncated after the completed plot index was written. Its damaged bytes were preserved; the exact frozen raw-page loop was used to recover that page, which matched the original indexed **227,651 bytes and SHA 5c93edd0…** exactly. The original delivery path was then restored with root authorization. No method, arrays, scales or scientific output changed. [RECOVERY.json](presentation_recovery/RECOVERY.json) documents the repair. All eight original paths now match the unchanged [PLOT_INDEX.json](results/PLOT_INDEX.json); [RESULTS_QA.json](RESULTS_QA.json) records verification.
