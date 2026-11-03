# C019: five-reference descriptive context on HD114783

The fixed comparisons support a recurrent barycentric spectral pattern in these seven existing observations. Every one of the 30 directed nonself merged records favors barycentric raw Pearson and normalized RMS in both the common core and surrounding region. The five references reuse seven observations: 30 directed rows represent 20 unordered observation pairs plus 10 reciprocal duplicates per frame/region. These shared rows do not create independent detections or a calibrated physical-origin test. All five original/current C019 labels remain U.

One frozen run completed at 18:55:09 UTC on 3 November 2026, after exact public method readback at commit `5c1c049f3c04906fd4fdd5480557b5007fc86dec` and root release. It retained 34 profiles, 180 comparison records, 20 identical-product self rows, 17 bounded source windows and 10 byte-exact original raw-panel copies. No profile is raw-only, blocked or structurally excluded; all 180 Pearson and 180 RMS values are evaluable. The 71 numerical ledger files include 61 NPZ files totaling 700,579 bytes. No numerical method, earlier output or classification was changed.

## Merged pattern and every fixed reference

These ranges include all 30 directed nonself records per frame/region and their shared observations; the medians are descriptive.

| Region / frame | Pearson min | Pearson median | Pearson max | RMS min | RMS median | RMS max |
|---|---:|---:|---:|---:|---:|---:|
| Common core / barycentric | 0.980520 | 0.990334 | 0.996033 | 0.048565 | 0.081760 | 0.110044 |
| Common core / topocentric | -0.703567 | 0.567238 | 0.985986 | 0.087638 | 0.957084 | 2.390775 |
| Surroundings / barycentric | 0.982541 | 0.992047 | 0.995497 | 0.062633 | 0.081537 | 0.122898 |
| Surroundings / topocentric | -0.070708 | 0.154936 | 0.992028 | 0.085375 | 1.581084 | 1.703967 |

Each of the five references keeps all six other epochs. March 22 and July 1 2023 remain observed cohort members without C019 discovery-reference status. Separate median correlations retain the reference identities; full six-row distributions and RMS values are in [the analysis report](../analysis/RESULTS_REPORT.md).

| Discovery reference | Core B median r | Core T median r | Surrounding B median r | Surrounding T median r |
|---|---:|---:|---:|---:|
| 0115 / 2022-01-21 | 0.988851 | 0.640985 | 0.991384 | 0.176403 |
| 0120 / 2022-02-05 | 0.986905 | 0.335617 | 0.992321 | 0.154936 |
| 0125 / 2022-05-05 | 0.990869 | 0.369223 | 0.991656 | 0.152480 |
| 0129 / 2023-01-16 | 0.991746 | 0.638316 | 0.993238 | 0.186813 |
| 0135 / 2023-05-15 | 0.989106 | 0.419723 | 0.991752 | 0.160549 |

The barycentric figures retain a rounded multi-sample central crest, positive-side depression and neighboring rise, embedded in a wider repeated sequence of peaks, troughs and a high positive-side plateau. Both fixed flank regions contain substantial structure. All seven curves and their amplitude/shape differences remain at full scale without masks or a selected epoch subset. The fixed topocentric interval samples a different moving pattern and reference levels; four predicted coherent centers leave its common core. No peak center, linewidth, lag, stellar velocity, continuum or origin model is fitted.

Topocentric agreement is not uniformly poor. January 21 2022 versus January 16 2023 retains r 0.985986 in the core and 0.992028 in the surroundings, with RMS 0.087638 and 0.085375; the close BERVs are retained in the metadata. Barycentric agreement remains better for that pair and for every other directed comparison. The global r ranges overlap between frames, so the result is pairwise descriptive agreement, not an origin threshold. Source/reference identities, reciprocal duplication and all 20 self rows remain explicit.

## Signed samples, reference levels and same-exposure native comparisons

All 34 profiles have 601 finite raw and normalized grid samples, valid positive pooled two-flank references and false low-reference flags. Wavelength-gap masks and outside-coverage masks are zero. Positive finite ERR samples are zero throughout. Every merged original window has 600 finite samples with 150 in each flank. Native order-3 windows contain 599–603 original samples and order-4 windows 500–502; these original sampling counts are distinct from the 601 interpolated grid centers.

Six order-4 frame profiles contain nonpositive original samples, all within their left reference flanks. The other 28 profile rows have zero window/flank nonpositive samples. The six signed outcomes are retained exactly:

| Event / frame | Window nonpositive / finite | Left nonpositive / finite | Right nonpositive / finite | Positive pooled reference | First-difference proxy |
|---|---|---|---|---:|---:|
| 0115 / barycentric | 1/500 | 1/123 | 0/127 | 106.930828 | 22.455254 |
| 0115 / topocentric | 1/500 | 1/123 | 0/127 | 106.930828 | 22.455254 |
| 0125 / topocentric | 10/500 | 10/123 | 0/127 | 57.970993 | 17.764269 |
| 0129 / barycentric | 1/501 | 1/124 | 0/127 | 120.701660 | 20.169325 |
| 0129 / topocentric | 1/500 | 1/123 | 0/126 | 122.095093 | 21.044978 |
| 0135 / topocentric | 5/500 | 5/123 | 0/126 | 57.727867 | 15.416144 |

A positive pooled median and a false low-reference flag do not imply that every individual sample is positive or provide a formal quality certificate. In particular, May 5 2022 topocentric order 4 retains 10 nonpositive left samples out of 123, and May 15 2023 retains 5/123. No clipping, sign flip, replacement flank or alternative normalization is introduced. The low-reference criterion remains a descriptive median/proxy rule; ERR absence and first-difference proxies do not establish formal uncertainties, significance or sensitivity.

Same-exposure native/merged comparisons are all retained. Their range summaries below cover every fixed native source in each order/frame; every core comparison uses 51 common samples and every surrounding comparison 550.

| Native order / frame | Core raw r range | Surrounding raw r range | Core RMS range | Surrounding RMS range |
|---|---|---|---|---|
| 3 / barycentric | 0.994359–0.998337 | 0.960072–0.968461 | 0.042266–0.067150 | 0.168869–0.203482 |
| 3 / topocentric | 0.994409–0.998436 | 0.965554–0.971345 | 0.042573–0.158110 | 0.169350–0.469004 |
| 4 / barycentric | 0.978095–0.991216 | 0.890441–0.896573 | 0.110397–0.128967 | 0.505656–0.605417 |
| 4 / topocentric | 0.972742–0.991864 | 0.892508–0.913056 | 0.103303–0.295005 | 0.582290–1.131556 |

Order 3 follows the same-exposure merged extraction more closely than order 4 in the surrounding pattern, while both retain broader scaling differences. In May 5 and May 15 topocentric order 4, surrounding RMS is 1.131556 and 1.089980 respectively despite raw r 0.910748 and 0.913056. Their positive references are 57.970993 and 57.727867 in unspecified native units; the native figures retain the high positive-side plateau and all signed left-flank values at full scale. Positive scalar division leaves raw Pearson invariant, while normalized heights/RMS depend on these structured fixed reference levels. No new fitted explanation or physical flux ratio is inferred. Native BUNIT is absent, merged ADU is uncalibrated, and shared extraction does not supply another independent observation, registration proof or origin validation.

## Exact geometry, original history and complete raw context

The exact original centers are 3881.6125 Å for 0115/0135, 3881.615 Å for 0120/0129 and 3881.6150000000002 Å for 0125. The catalog-extrema midpoint remains 3881.6137500000004 Å. Its ±0.25 Å core [3881.3637500000004,3881.8637500000004] and ±3 Å context [3878.6137500000004,3884.6137500000004] were fixed before values, with 41/440 support gates. The common metric core differs from original edges by up to 0.00125 Å; it does not contain their full union or measure physical linewidth. Exact original cores/markers are preserved separately inside the broader context without expansion or recentering.

The first-queue January 21 discovery at BERV 29.658729150824 km/s fixes the wavelength-specific topocentric anchor 3881.2297765555622 Å; all five references remain. The seven observations span 59.073251754930496 km/s. Independently frozen common-center predictions are inside for January 21 zero, February 5 +0.038546984 and January 16 2023 −0.004533438 Å, and outside on the positive side for May 5 2022 +0.552591733, March 22 2023 +0.266583857, May 15 +0.606667375 and July 1 +0.760325116 Å. Those seven predicted centers have a three-inside/four-outside pattern. The five original discovery markers instead have three inside/two outside, because March 22 and July 1 are non-reference epochs. Markers use each original center and own discovery BERV; they are not fitted peak locations or full finite-feature coverage. Fixed windows can include neighbors after a coherent center leaves the core.

Fresh 360-header scans selected only orders 3 and 4 in each of five discovery products. All ten original mapping contexts retain true original global/local/baseline verification and U/U/U reviews. Eight batch03 later-five-window fields are explicitly true. **0129's two later fields remain absent/null/unassessed**, with field presence false and no selection in the wider mapping follow-up. Null is neither failure nor inferred later support. Its original secondary U normalized to U, adopted baseline U/current U and original mapping_verified basis remain separate from batch03 baseline_mapping_verified. No distinct 0128 I/M history or order-2 limitation is transferred.

I inspected all eight exact frozen PNGs at original resolution: merged broad/core, three native pages and three original raw/excess pages. All ten raw contexts and complete stored extents remain. Most show a central extended positive patch with a trace-like vertical band, clearer in order 3 and noisier in order 4. The remote high-left bright pixel in 0135 order 3 dominates its full raw/excess color scale and leaves its central enhancement faint; that deposit does not classify the central feature. Original 0129 21×25 five-array containers (3,253/3,059 bytes) remain distinct from batch03 31×33 panels. No new crop, contrast variant, subtraction, background fit, pixel statistic, registration or origin assignment was introduced.

These observations and original epoch/profile/raw evidence already existed. C018 uses the same seven observing products at a disjoint bounded spectral window; this disjointness does not create independent observations or establish independence of all historical crops. C005 overlaps numerically on HD106515A and shares no products or source pixels. Completed mapping/normalization diagnoses remain complete. The independent actual reconstruction passes 1,026 checks over 134,487 scalar values, including all 34 profiles, 180 comparisons and ten exact original raw copies; source metrics agree exactly. Arithmetic agreement validates reproduction of this descriptive method, not physical origin, a qualified laser candidate or a calibrated survey null.

## Next fixed original-queue route

The pre-value handoff remains [C021/R022](NEXT_STEP.md), original queue row 35, full members 0116/0121/0126/0130/0139 at 35/40/44/48/55. Same seven observations, but July 1 replaces C019's May 15 discovery reference. Its proposed exact midpoint is 4309.82625 Å and own January anchor 4309.39991731037 Å; 30 directed nonself rows represent 20 unordered pairs plus 10 reciprocal duplicates per frame/region. Exact members, original cores, five markers and reference identities remain fixed before any future values.

C021 history is distinct: original order-19 local/baseline gates are false for 0116/0126/0130 and true for 0121/0139, with global and later support true separately. Four batch03 events originally have U/U/U; **0130 originally has primary I, secondary M normalized I and adopted baseline I, then later unchanged-coordinate U/U/current U** after its completed wider mapping diagnosis. Do not transfer current 0129's absent later fields or all-original-true history to 0130, rewrite original failures or replay that completed diagnostic. Completed C013/0092 and C014/0104 normalization routes remain skipped. No C021 values were read or executed here; Rubin's limited feasibility/minimum-50 state is unchanged.

[The numerical ledger](../analysis/results/OUTPUT_HASHES.json) remains SHA256 `e4c43d247db9bf5cd27ba4e6c7501de91ac8b57293b1f5d563e03f3d4be919ac`. [All comparisons](../analysis/results/COMPARISONS.json), [plot index](../analysis/results/PLOT_INDEX.json), [independent actual audit](../independent_audit/NUMERICAL_AUDIT.json), [pre-array review](PRE_ARRAY_SCIENTIFIC_REVIEW.json) and [final method review](FINAL_METHOD_REVIEW.json) preserve the fixed evidence and limits.
