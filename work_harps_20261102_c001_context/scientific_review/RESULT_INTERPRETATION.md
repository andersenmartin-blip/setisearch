C001/HD103991 remains unresolved (U for V2E2-0001 and V2E2-0016). The fixed broader context separates a central crest that aligns more closely topocentrically in several comparisons from surrounding structure that generally aligns more closely barycentrically. It does not establish a physical origin or justify another fitting variant.

This reading covers the released 20 profiles and 64 comparisons completed on 2026-11-02 at 14:06:17 UTC, following public method commit `c7e53d0180887618817923cfb1bec4b5b300ad53`. Six existing merged exposures, both discovery references, both frames, both native covering orders for each discovery, and all four historical raw panels remain accounted for. No source was blocked; four native/frame slots correctly remained raw-only. The broad, core and native-order figures were independently inspected; the plot owner's four-panel inspection is consistent with this reading.

Quality comes first. All 12 merged profiles have 601 finite grid values, positive two-sided flank references of 74.14–124.43 ADU and no low-flank-reference flag; first-difference noise proxies are 13.75–17.84 ADU. These structured flanks are reference levels, not demonstrated quiet continua. There are no positive finite ERR samples, so the proxies and correlations are descriptive, without a calibrated significance or likelihood interpretation. Positive scalar normalization cannot create the reported Pearson frame differences.

The fixed core is |offset|≤0.265 Å; the surrounding pattern is 0.265<|offset|≤3 Å. Excluding self comparisons, the results retain both references:

| Discovery reference (observation date) | Region | Median r, barycentric | Median r, topocentric | Pairwise direction across five other epochs |
|---|---|---:|---:|---|
| V2E2-0001 (2023-02-22) | Core | 0.504765 | 0.795469 | Topocentric higher 5/5 |
| V2E2-0001 (2023-02-22) | Surrounding pattern | 0.932862 | 0.863740 | Barycentric higher 4/5 |
| V2E2-0016 (2023-02-28) | Core | 0.839913 | 0.837973 | Topocentric higher 3/5; barycentric higher 2/5 |
| V2E2-0016 (2023-02-28) | Surrounding pattern | 0.934338 | 0.910320 | Barycentric higher 5/5 |

For the two discovery exposures directly, core r is 0.491621 barycentric versus 0.795469 topocentric; surrounding-pattern r is 0.936738 versus 0.844334. Normalized RMS has the same direction for that pair: core 0.713015 versus 0.571776, surrounding pattern 0.220161 versus 0.341328. The figures show the narrow central crest more tightly aligned topocentrically and extensive neighboring structure better aligned barycentrically. The second reference demonstrates that the core preference is not universal. These are whole-region correlations, not a measured isolated-line origin, width, or calibrated model comparison. The two reference sets reuse exposures and include the same discovery pair twice; their counts are not independent trials.

Native order2 closely follows the same-exposure merged profile (core r 0.989–0.992; surrounding pattern 0.985–0.986). This is extraction consistency from shared photons, not an independent observation. All four order3/frame slots lack the left normalization flank entirely; only 391–394 of 601 grid values are covered. The right-flank median is 11.70–17.14 in unspecified native units, comparable to a 13.11–14.73 noise proxy, and approximately 18–24% of the retained native-window values are nonpositive. The signed plots show a jagged low baseline rather than a clean repeated crest. Core raw correlations of 0.181–0.225 remain computable from 53 common points, but the broader comparison fails its fixed coverage requirement and normalized RMS is unavailable. Missing coverage is the new normalization block; historical low/nonpositive local-flux context remains a separate limitation. The merged low flags cannot validate order3. Native and merged units/extractions do not support a calibrated flux ratio.

The available BERV span is only 3.193229 km/s, or 1.224918 nominal resolution elements. Together with reference dependence, shared observations, absent error calibration and the order3 limitation, this supports a mixed descriptive frame pattern, not a terrestrial, stellar, instrumental or artificial-origin assignment. Both U labels and historical mapping decisions remain unchanged. This bounded C001 context is complete; the next action follows the original queue, as specified in NEXT_STEP.md.

Evidence binding (SHA-256; paths relative to this phase):

- `analysis/results/SUMMARY.json`: `b7c7be91aa22706b2aedef5e5cc53ad249a6ed1f6b8ebf561d6d3d3a8a745961`
- `analysis/results/PROFILE_METRICS.json`: `a84b3371847fe00a3a00f9a4e7114502eba6a8242b11cc476964c472d2069c23`
- `analysis/results/COMPARISONS.json`: `9439353f91a74d01381a789dff5636e5e5a2804eb4b5aa27bb9b33ab14d7636e`
- `analysis/results/PLOT_INDEX.json`: `7fb005ae4196849f0924ce8c7e6611d482a49dae6852284f3b9c208c93229914`
- `analysis/results/PRESERVED_RAW_CONTEXT.json`: `b9b5800ee68a0bbb7e137c5e31893c61c267a766615dc46a1c375b388784577d`
