C005/HD106515A remains U for all five records. The central feature and the broader neighboring pattern recur closely in barycentric coordinates across seven existing epochs and all five discovery references. Both native covering orders retain supporting same-exposure shape context, with measurable order-dependent differences and two low-reference flags. This is descriptive spectral consistency, not a physical-origin or laser classification.

The single released run completed on 2026-11-02 at 16:33:38 UTC after public method commit `b9e06d67e3a499dd93bf1b718820a18b0ddbe395` and exact readback of 33 files. All 34 profiles have 601 finite grid points and valid positive normalization references; all 180 Pearson and 180 normalized-RMS outcomes are evaluable, including 20 identical-product self comparisons. No source, normalization or native covering-order slot was dropped. Ten historical raw contexts remain preserved. Full support and positive normalization do not establish uniformly high quality.

All 14 merged profiles and ten native order3 profiles have no low-reference flag. Merged flank references span 119.28–544.85 ADU, with first-difference noise proxies 18.42–42.47 ADU. Native order4 has two flagged profiles, both in the fixed topocentric frame:

| Event / observation date | Positive reference, native units | Noise proxy, same units | Reference/proxy | Nonpositive source-window samples |
|---|---:|---:|---:|---:|
| V2E2-0035 / 2022-05-07 | 40.547943 | 16.196479 | 2.503504 | 2.99% |
| V2E2-0054 / 2023-07-03 | 32.033684 | 16.202098 | 1.977132 | 4.98% |

These satisfy the frozen low-reference rule (reference≤3×proxy) while retaining positive, sufficiently sampled normalization. The same exposures' barycentric order4 windows are unflagged, with ratios 5.113849 and 3.885056. The frames sample different fixed flanks; this is not a measured physical change between two observations of the same epoch. The low flags must remain visible alongside correlations, but are not coverage failures or reasons to alter the method. No positive finite ERR samples exist in any of the 34 profiles, and the proxy is not formal SNR or calibrated uncertainty. The structured flanks are reference levels, not established quiet continua.

Median raw Pearson against the six other epochs retains every fixed discovery reference. The shared core is |offset|≤0.2525 Å (51 sampled centers), with surrounding pattern 0.2525<|offset|≤3 Å (550 centers):

| Discovery reference | Core, barycentric | Core, topocentric | Surrounding, barycentric | Surrounding, topocentric |
|---|---:|---:|---:|---:|
| V2E2-0023 · 2022-01-05 | 0.948681 | −0.062313 | 0.971425 | 0.167409 |
| V2E2-0029 · 2022-03-07 | 0.987626 | −0.248398 | 0.983516 | 0.298419 |
| V2E2-0035 · 2022-05-07 | 0.985985 | 0.154541 | 0.987088 | 0.360436 |
| V2E2-0046 · 2023-03-22 | 0.989248 | −0.098214 | 0.985375 | 0.392800 |
| V2E2-0054 · 2023-07-03 | 0.984982 | −0.214093 | 0.980731 | 0.123611 |

Across all nonself comparisons, barycentric core r spans 0.912055–0.994226 and surrounding r spans 0.947577–0.994515. Barycentric r exceeds topocentric r for five of six other epochs against the first reference and six of six against every other reference, in both regions. The exception is the 2022-12-31 observation, only 0.237026 km/s from the first discovery in BERV: core r is 0.912055 barycentric versus 0.924846 topocentric; surrounding r is 0.947577 versus 0.950189. Reused and reversed pairs are not independent trials. The five catalog records, shared exposures and repeated reference comparisons cannot be multiplied into independent detections.

The first-discovery topocentric anchor stays fixed at 3881.647279 Å. Across the 59.609813 km/s BERV span, a barycentric-coherent feature is expected to move as far as +0.768821 Å from it, outside the fixed core in four of seven epochs, including references 0035/0046/0054. Their topocentric-core correlations therefore concern the anchor neighborhood, potentially another feature, rather than their own recentered discovery peak. The broader windows retain the displaced pattern. All eight figures were inspected: the central crest and neighboring structures align closely barycentrically, while the fixed topocentric displays separate those structures. No recentering, fitted width or lag was introduced.

Same-exposure native order3 correlations with the merged extraction are 0.993281–0.997261 in the core and 0.945941–0.968422 in the surroundings. Order4 is less consistent over the broad window: core r is 0.965275–0.991654 and surrounding r is 0.866191–0.905812. Native/merged normalized curves retain different relative levels in the broad plateau near +2 Å: order3 lies lower and order4 higher than the merged profile after their separate scalar reference scaling. This is not a perfect whole-window match and should not be attributed solely to random noise. Order4's two low-reference topocentric profiles still have high core Pearson values, but core normalized RMS is approximately 0.445 and 0.765, and surrounding RMS approximately 0.966 and 1.004. High correlation does not remove reference-level or extraction-shape limitations. Positive scalar division alone cannot change Pearson; normalized amplitudes/RMS are shape context, not calibrated flux ratios. Native units are unspecified, and these reductions share the same observations.

The ten preserved historical raw contexts include central, spatially extended trace-associated enhancements and separate off-center spots. Distinct spots in 0023/order4,0029/order4 and 0054/order3 dominate their individual display scales; the noisier 0054/order4 context remains. Those spots are not identified physically or conflated with the central structure. Primary, secondary and adopted historical descriptions remain separate records. No new raw subtraction, mapping, detector statistic or origin classifier was applied.

One raw-context PNG initially failed decoding; its damaged bytes were preserved and the original path restored to the exact originally indexed 227,651-byte image, SHA-256 `5c93edd004ef688eec300f257b8815b33ca3f701929e5d1d13459d186ec381b9`. The restored original was independently viewed, completing eight-figure inspection. This presentation recovery changed no analysis, pixels selected or plot settings; its receipt remains in `analysis/presentation_recovery/RECOVERY.json`.

The supported conclusion is recurring barycentric spectral morphology with explicit order-dependent quality, reference scaling and shared-data limitations. The nominal 22.866-resolution-element BERV span is not calibrated discrimination power. Physical emitter, intrinsic linewidth, false-alarm rate and sensitivity remain undetermined. All five U labels and earlier pipelines remain unchanged. C005 is complete without further variants; NEXT_STEP.md follows the prospectively selected C006 group.

Evidence binding (SHA-256, paths relative to this phase):

- `analysis/results/SUMMARY.json`: `f78db222797c96b106affd3b344917bb47eb6c85bd58457c7f710df8d7e67003`
- `analysis/results/PROFILE_METRICS.json`: `2f77272574692c10d8e1910f9cd56891f92d1acfcdea9c5b9663e24fd97f90d7`
- `analysis/results/COMPARISONS.json`: `dfb9f6e690c41448aba9bb20777f146817c04c246741d3dca39d0f2ed567f85d`
- `analysis/results/PLOT_INDEX.json`: `e5edb6b01ad2b790f2ae72a34eb4fa26bdf65756e1b135cb7766e8aaef445cc9`
- `analysis/results/PRESERVED_RAW_CONTEXT.json`: `54df2748b7df1a50c2d869c16bc5ae0f64b6fa2251cb55cbb02b99ae521bdb69`
