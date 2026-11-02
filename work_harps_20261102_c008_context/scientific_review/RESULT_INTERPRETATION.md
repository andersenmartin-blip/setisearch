# C008 scientific interpretation

The fixed C008 context shows a recurring asymmetric shoulder/bump near 5182.005 Å within an extended structured spectrum across all seven reused HD106515A epochs. Each of the six nonself epoch comparisons has higher raw Pearson correlation and lower normalized RMS in barycentric coordinates than in the one fixed topocentric frame, in both the original core and surrounding window. **V2E2-0047 remains U.** These comparisons establish neither a line identity nor a physical origin, qualified laser candidate or calibrated null.

The exact method was public and read back before computation at commit `d194c32c3679cebb485f901ceccd1ac4786d66f6`, with PLAN SHA-256 `22824f0319684b6c27022023946f2806cdd00d4604dc74493f8b7f074e2bf31f`. The single released execution retains 16 measured profiles and 32 comparisons, including four identical-product self rows, eight bounded source windows and one exact historical raw-panel copy. No profile is raw-only, blocked or structurally excluded. All 32 raw Pearson and 32 normalized RMS values are evaluable; the self rows add no independent recurrence evidence.

## Complete merged comparison

Each range below includes all six other epochs against the one fixed March 2023 discovery product, excluding the self rows.

| Frame | Region | Raw Pearson r range | Normalized RMS range |
|---|---|---:|---:|
| barycentric | Original core | 0.844156–0.978778 | 0.017774–0.084750 |
| barycentric | Surrounding pattern | 0.992765–0.999513 | 0.016782–0.067710 |
| topocentric | Original core | 0.336330–0.692322 | 0.157832–0.509993 |
| topocentric | Surrounding pattern | 0.806281–0.905966 | 0.275959–0.447996 |

**January 2022 is the weakest barycentric agreement in both regions**, with core r = 0.844156 and RMS = 0.084750, and surrounding r = 0.992765 and RMS = 0.067710. It remains in every range, table and plot. Its scaled core contains deeper neighboring depressions and differs visibly from the more closely aligned later profiles. No quality-based exclusion or alternative reference was selected.

The core figure shows a shallow asymmetric bump or shoulder on a substantial structured flux level, followed by a trough around +0.08 Å. It is not a visually isolated narrow spike. The wide figure includes an extended decline, several dips at negative offsets and a deep trough around +2 Å. **The very high surrounding correlations describe this full pattern**, including those large-scale changes, rather than independently isolating the catalog feature. No contribution decomposition, fitted line profile, measured linewidth or physical-line identification was made.

## Structured reference levels and signed quality

All 16 profiles retain the complete 601-point raw and normalized grid, valid positive references, false low-reference flags and zero positive finite ERR samples. Window and both-flank nonpositive source fractions are zero for every profile. All comparisons use the full 51 core or 550 surrounding grid points, above the unchanged minima of 41/440. These are support and reference diagnostics, not calibrated significance or absence-of-systematics tests.

Merged reference levels span 2,321.091–7,666.803 ADU, while their descriptive first-difference proxies span 59.501–123.512 ADU. The deep trough near +2 Å lies inside the fixed positive reference interval [+1.5,+3] Å. The negative interval samples a distinctly higher, also structured region. For the discovery merged spectrum, the left and right medians are **12,489.915527 and 4,293.377930 ADU**, while the pooled reference is **6,797.728760 ADU** in both frames. This is a median of the pooled samples, not an established line-free continuum or a fitted baseline. A scaled core level near 1.6 therefore is not a calibrated emission excess over a known continuum.

The native order has 101 finite left-flank and 104 finite right-flank samples, with medians 17,151.376953 and 6,103.837646 and pooled reference 9,506.636719 in unspecified extracted units. Its descriptive first-difference proxy is 218.302328 in both frames. These values differ from merged ADU because the extraction scales and units differ; no physical flux ratio is inferred. Positive scalar normalization leaves Pearson unchanged, while scaled heights and RMS depend on the fixed reference level. No mask, moved flank, clipping, sign change or fitted correction was introduced.

## Native and raw context

Fresh checks of all 72 native order headers identified only order 43 covering the original center; it covers the full context in both frames. Native-to-merged core r is **0.999404 in both frames**, with normalized RMS **0.007621**. Surrounding r is **0.999582** in both frames, with RMS **0.021340 barycentric / 0.021340 topocentric** at six decimals. The full native figure preserves the same extended decline and deep trough, with small scaled extraction differences. Shared extraction lineage makes this agreement dependent evidence, not another observation or a physical-origin validation.

The preserved full raw cutout contains a faint central vertical band, while **two much brighter structures at the far right edge dominate its full displayed scale**. The unchanged residual panel likewise retains those strong edge structures, with the central residual subdued at that scale. The historical primary and secondary descriptions explicitly concern the central or enlarged-center context: a broad asymmetric shoulder and smooth trace-width increase against structured levels. Those descriptions must not be substituted for the appearance of the complete panel. All original pixels and the historical subtraction remain present; no new assignment of the edge structures to the catalog event, pixel statistic, registration, subtraction, spatial model or physical origin was made.

All four historical global, local, baseline and later five-window mapping flags are true for order 43. They remain distinct historical diagnostics; no new mapping test was performed and no origin follows from their agreement. The original primary, secondary and root-adopted U classifications remain unchanged.

## Fixed frame and prior-data dependence

The only discovery is observed on 2023-03-22, with BERV 3.26509772194068 km/s, giving the wavelength-specific fixed topocentric anchor **5181.9485623946 Å**. The expected barycentrically coherent center is outside the fixed ±0.25 Å topocentric core for January 2022 (−0.464455 Å), May 2022 (+0.382991 Å), December 2022 (−0.468551 Å), May 2023 (+0.478365 Å) and July 2023 (+0.561819 Å). March 2022 (−0.129746 Å) and the March 2023 discovery are inside. These are prospective metadata coordinates, not fitted peak positions. The core remains fixed, so an epoch's comparison can concern neighboring structure when the expected catalog feature is displaced outside it. The BERV span is coordinate separation, not a calibrated origin test.

The bounded C008 wavelength window [5179.005,5185.005] Å is disjoint from the previous C001–C007 bounded windows. Nevertheless, original epoch/profile and raw evidence for 0047 already existed, and all seven observing products are reused. A distinct wavelength window does not make this blind, untouched or independent validation and adds no observing time or archive completeness. All fixed reference-flank structure remains included.

The absent positive ERR support and descriptive first-difference proxies provide no formal uncertainty model, significance, false-alarm probability, sensitivity estimate or qualified survey null. The catalog template width was not measured as a physical linewidth. High profile correlations and historical mapping support do not change these limits.

## Verification and handoff

All four figures were visually inspected, including complete titles and the seven-epoch legends, both native views and the entire raw/excess pair. Their full PNG decoding, bytes and hashes agree with the unchanged plot index. All **45 frozen source bindings and 35 numerical output hashes** remain exact. The independent arithmetic audit passes **424 checks across 63,374 scalar values**, without importing production functions. This verifies computational consistency, not human peer review or new observing evidence.

The next original-queue choice was fixed before C008 results: **C009 / V2E2-0050**, singleton row 18 at 6802.02 Å, with the same March 2023 discovery observation. Its handoff preserves the historical primary A and secondary A votes alongside the root-adopted **U**, which retained the unresolved possible artifact/spectral blend. That distinction is not a new classification or permission to promote the next record. No C009 analysis was executed here.
