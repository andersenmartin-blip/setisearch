# C003: HD106515A joint spectral context

The central feature and the wider structured spectrum align closely in the barycentric frame across all seven existing cohort epochs. This holds against every one of the five discovery references. Native order 3 closely matches its same-exposure merged spectrum; the three covering order 2 contexts are noisier and incomplete. These are descriptive shape and internal-consistency results. **All five C003 records remain U; no origin or line-width classification is assigned.**

The released, single execution completed on **2026-11-02 at 14:54:08 UTC**: **30 profiles, 172 comparisons, 20 identical-product self-comparisons**, zero blocked source profiles and six raw-only normalization slots. Eight historical raw-panel pairs remain. Two native order 2 contexts are structural exclusions, not failed measurements. Scope is all seven HD106515A spectra in the original extension02 cohort, not archive-wide completeness.

## Fixed coordinates and all five references

The shared barycentric air-wavelength center is **3869.75125 Å**, with one first-discovery topocentric anchor at **3869.3622643053627 Å**. The ±3 Å grid has 601 centers at 0.01 Å spacing. Its fixed nominal ±0.25625 Å union core selects 51 centers (−0.25 to +0.25 Å); the surrounding comparison uses the remaining 550. Signed flux is retained, with separate positive pooled-median scaling in the unchanged 1.5–3 Å flanks when both sides contain at least 20 finite native samples. No continuum, width, lag, center, stellar velocity or instrumental drift was fitted.

The table gives **minimum–maximum over all six nonself epochs for each reference**. B/T means barycentric/topocentric. Every reference remains; these ranges are descriptive summaries of the frozen pair metrics, not new detection statistics. The 20 self-comparisons remain in the full output with r=1 and RMS=0. Reversed discovery pairs share data and are not independent.

| Reference (observation date) | Region | r B range | r T range | Normalized RMS B range | Normalized RMS T range |
|---|---|---:|---:|---:|---:|
| 0022 (2022-01-05) | Core | 0.941–0.965 | -0.640–0.984 | 0.185–0.310 | 0.129–1.612 |
| 0022 (2022-01-05) | Surroundings | 0.928–0.966 | -0.079–0.945 | 0.177–0.259 | 0.227–1.030 |
| 0027 (2022-03-07) | Core | 0.956–0.988 | -0.458–0.648 | 0.113–0.221 | 0.524–1.460 |
| 0027 (2022-03-07) | Surroundings | 0.950–0.990 | 0.027–0.179 | 0.099–0.222 | 0.911–0.951 |
| 0044 (2023-03-22) | Core | 0.941–0.988 | -0.401–0.027 | 0.113–0.241 | 1.087–1.513 |
| 0044 (2023-03-22) | Surroundings | 0.951–0.990 | 0.029–0.225 | 0.099–0.218 | 0.809–0.944 |
| 0051 (2023-05-24) | Core | 0.946–0.988 | -0.662–0.362 | 0.151–0.277 | 1.032–1.612 |
| 0051 (2023-05-24) | Surroundings | 0.945–0.985 | 0.052–0.363 | 0.123–0.227 | 0.789–0.963 |
| 0053 (2023-07-03) | Core | 0.943–0.983 | -0.567–0.362 | 0.151–0.310 | 1.032–1.663 |
| 0053 (2023-07-03) | Surroundings | 0.941–0.983 | -0.069–0.363 | 0.134–0.240 | 0.789–1.025 |

Across these nonself comparisons, barycentric core r spans **0.9407–0.9880** and surrounding r **0.9281–0.9899**. The plots show the central crest aligned with a repeated wider sequence of peaks and troughs, rather than a feature considered in isolation. There is an explicit near-BERV exception to a simple frame ranking: the 2022-12-31 observation against reference 0022 has core r **0.9646 B / 0.9835 T** and surrounding r **0.9281 B / 0.9455 T**.

**The topocentric core is a fixed coordinate window, not each later discovery’s recentered feature.** Header-derived conversion places the common feature center outside that core for four of seven epochs, including references 0044, 0051 and 0053. Their core metrics can therefore compare neighboring structure at the anchor. Offsets reach 0.7664 Å; these are metadata predictions, not newly fitted centers. The 59.610 km/s BERV span (22.866 nominal resolution elements) does not calibrate an origin test. All five references and both frames are retained without a favorable-reference choice.

All 14 merged profiles have complete 601-point support, positive flank references **130.08–317.40 ADU**, descriptive noise proxies **18.39–32.26 ADU**, false low-reference flags and zero nonpositive window samples. The flanks remain structured spectral reference regions, not established quiet continuum. Positive scalar normalization cannot itself change Pearson correlation.

- [All seven epochs: ±3 Å context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same profiles: fixed core close-up](results/figures/MERGED_CORE_CONTEXT.png)

## All eight native-order contexts

These comparisons use each native order’s own exposure’s merged product. Their common extraction lineage prevents interpreting agreement as an independent observation. Native BUNIT is absent: values below are in **unspecified native extracted units**, whereas merged flux is explicitly ADU. No physical cross-order or native/merged flux ratio is inferred.

Values separated by `/` are B/T. Order 2 levels marked `*` are the available **left-only** medians, not valid normalization divisors. Order 3 levels are valid pooled-flank references. Grid coverage is out of 601; nonpositive percentages use finite source-window samples.

| Event/order | Grid B/T | Flank level B/T | Noise proxy B/T | Nonpositive % B/T |
|---|---:|---:|---:|---:|
| 0022/2 | 365 / 365 | 44.24* / 44.24* | 14.51 / 14.51 | 2.70 / 2.70 |
| 0022/3 | 601 / 601 | 180.93 / 180.93 | 24.25 / 24.25 | 0.00 / 0.00 |
| 0027/2 | 340 / 365 | 78.29* / 90.65* | 14.61 / 15.83 | 1.57 / 1.47 |
| 0027/3 | 601 / 601 | 287.60 / 295.34 | 29.68 / 30.37 | 0.00 / 0.00 |
| 0044/2 | 330 / 365 | 82.78* / 98.48* | 18.30 / 19.29 | 1.35 / 1.23 |
| 0044/3 | 601 / 601 | 282.39 / 279.99 | 35.16 / 34.70 | 0.00 / 0.00 |
| 0051/3 | 601 / 601 | 198.44 / 180.11 | 24.26 / 24.20 | 0.00 / 0.00 |
| 0053/3 | 601 / 601 | 158.65 / 155.80 | 20.25 / 20.18 | 0.00 / 0.00 |

Every selected order 3 profile has full coverage, a usable positive reference and a false low-reference flag. Every selected order 2 profile lacks the right flank entirely and remains **RAW_ONLY: MISSING_RIGHT_FLANK_COVERAGE**. This geometric failure does not establish nonpositive continuum. The three order 2 core windows still have all 51 points, but their surrounding coverage is only 314/550 (0022), 289 B / 314 T (0027) and 279 B / 314 T (0044), below the fixed 440-point gate. Their normalized RMS and broad raw correlation are therefore blocked.

| Event/order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 0022/2 | 0.8752 / 0.8752 | blocked / blocked | blocked / blocked | blocked / blocked |
| 0022/3 | 0.9995 / 0.9995 | 0.9900 / 0.9900 | 0.0395 / 0.0395 | 0.0989 / 0.0992 |
| 0027/2 | 0.8674 / 0.8871 | blocked / blocked | blocked / blocked | blocked / blocked |
| 0027/3 | 0.9998 / 0.9996 | 0.9906 / 0.9895 | 0.0237 / 0.0276 | 0.1018 / 0.1087 |
| 0044/2 | 0.8878 / 0.9544 | blocked / blocked | blocked / blocked | blocked / blocked |
| 0044/3 | 0.9998 / 0.9997 | 0.9913 / 0.9880 | 0.0485 / 0.1403 | 0.0939 / 0.1213 |
| 0051/3 | 0.9998 / 0.9997 | 0.9928 / 0.9900 | 0.0316 / 0.0370 | 0.1068 / 0.1102 |
| 0053/3 | 0.9995 / 0.9994 | 0.9931 / 0.9898 | 0.0315 / 0.0464 | 0.1003 / 0.1021 |

Order 3’s same-exposure core r is **0.9994–0.9998** and surrounding r **0.9880–0.9931**; the raw and separately scaled curves closely overlay the merged pattern. Its core normalized RMS spans 0.0237–0.1403 and surrounding RMS 0.0939–0.1213. The covering order 2 curves preserve weaker, noisier versions of the pattern, with core r = 0.8674–0.9544, missing right-side coverage and no normalized comparison. A high same-exposure topocentric correlation still describes that fixed anchor window.

Order 2 for 0051 and 0053 was not measured: original feature centers 3870.0700818 and 3870.1324023 Å exceed their respective endpoints 3870.0060516 and 3870.0057692 Å. The first-anchor coordinate falling inside those orders does not make them line-covering. [NATIVE_ORDER_SCOPE.json](results/NATIVE_ORDER_SCOPE.json) preserves the full included/excluded metadata; no substitute partial-order profile or raw panel was created.

- [Native profiles, page 1: 0022 and 0027](results/figures/NATIVE_ORDERS_1.png)
- [Native profiles, page 2: 0044, 0051 and 0053](results/figures/NATIVE_ORDERS_2.png)

## Preserved raw context and limits

All eight original raw cutouts and historical excess maps were copied exactly. Central trace-column enhancements are visible, particularly in order 3; order 2 has lower contrast. Separate compact off-center spots in **0027/order 2 and0044/order 3** dominate those panels’ full-value color scales and must not be conflated with the central enhancement. Their physical origin is not assigned. The stored raw-excess subtraction and separate scales are historical context; no new detector mapping, subtraction, charge statistic or morphology classifier was applied.

- [Preserved raw panels, page 1: 0022 and 0027](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png)
- [Preserved raw panels, page 2: 0044, 0051 and 0053](results/figures/PRESERVED_RAW_ORDER_CONTEXT_2.png)

All 30 profiles have **zero finite positive ERR samples**. The first-difference noise proxy supplies no formal uncertainty, significance or false-alarm rate. The five overlapping records reuse seven exposures, and native/merged pairs share an exposure. None of these comparison counts is an independent-detection count. No free-width model, calibrated sensitivity, physical flux or completeness was inferred; historical pipelines and labels remain unchanged.

## Reproduction and visual QA

The [independent numerical audit](../independent_audit/NUMERICAL_AUDIT.json) passed **807 checks over 117,053 scalar values**, reconstructing all 30 profiles, 172 comparisons, 15 bounded inputs and eight raw copies without importing production functions. Maximum normalized-profile difference was 1.31×10⁻¹¹; maximum comparison difference was 6.60×10⁻¹⁴. All 48 frozen sources remained exact.

The method was public before execution at commit `d1046d8306ba34699f0eab9af57be145316eef76`. [PLAN.json](PLAN.json), [ROOT_RELEASE.json](ROOT_RELEASE.json), [SUMMARY.json](results/SUMMARY.json) and [OUTPUT_HASHES.json](results/OUTPUT_HASHES.json) bind the run. [BOUNDED_INPUT_INDEX.json](results/BOUNDED_INPUT_INDEX.json) identifies the compact source-coordinate/flux/error arrays. [PROFILE_METRICS.json](results/PROFILE_METRICS.json) and [COMPARISONS.json](results/COMPARISONS.json) retain every detailed value, support count and blocked reason.

All six frozen-script originals were visually inspected. Separate margin crops confirm the full core title, fixed-anchor caveat and seven-epoch legend are present in the saved 1820×1120 PNG; native labels are also complete. No layout amendment was needed. [PLOT_INDEX.json](results/PLOT_INDEX.json) binds all six images; [RESULTS_QA.json](RESULTS_QA.json) verifies source/output preservation and report links.
