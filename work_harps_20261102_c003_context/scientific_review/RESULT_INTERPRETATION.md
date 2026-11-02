C003/HD106515A remains U for all five records. The new joint context shows a recurring central feature embedded in a recurring broader barycentric spectral pattern across seven existing epochs. The agreement persists across all five discovery references. It strengthens that descriptive account without establishing the emitter, an intrinsic linewidth, or a qualified laser candidate.

The single released run completed at 2026-11-02 14:54:08 UTC after method commit `d1046d8306ba34699f0eab9af57be145316eef76` and exact readback of 31 files. All 30 profiles and 172 comparison outcomes are present, with no source blocked. Twenty comparisons are identical-product self records. Eight historical covering-order contexts and two structurally noncovering order2 exclusions remain distinct. Of the recorded comparisons, 166 have raw Pearson values and 160 have normalized RMS values; no missing outcome was replaced.

Quality is adequate for the specified descriptive merged/order3 comparisons. All 14 merged and ten native order3 profiles have full 601-point coverage, positive two-sided flank references and no low-reference flag. Merged references range from 130.08 to 317.40 ADU, with first-difference noise proxies 18.39–32.26 ADU. The flanks contain spectral structure and are not established quiet continua. No positive finite ERR samples are available. The fixed noise proxy therefore does not supply formal SNR or calibrated uncertainty. The actual results do not convert historical merged quality flags into a native-order guarantee.

Median unshifted raw Pearson against the six other epochs is reported for every discovery reference. The core is the fixed union |offset|≤0.25625 Å (51 sampled centers); surrounding pattern is 0.25625<|offset|≤3 Å (550 centers):

| Discovery reference | Core, barycentric | Core, topocentric | Surrounding, barycentric | Surrounding, topocentric |
|---|---:|---:|---:|---:|
| V2E2-0022 · 2022-01-05 | 0.950983 | −0.044838 | 0.956488 | 0.132083 |
| V2E2-0027 · 2022-03-07 | 0.984224 | 0.143348 | 0.981953 | 0.088721 |
| V2E2-0044 · 2023-03-22 | 0.982358 | −0.188589 | 0.983450 | 0.200192 |
| V2E2-0051 · 2023-05-24 | 0.981103 | −0.326308 | 0.979672 | 0.174217 |
| V2E2-0053 · 2023-07-03 | 0.978759 | 0.076522 | 0.977921 | 0.233720 |

Every nonself barycentric core r lies between 0.940696 and 0.988011; surrounding-pattern r is 0.928074–0.989934. The first reference has barycentric r higher for five of six other epochs in each region; the remaining references have six of six. The exception is the 2022-12-31 exposure, only 0.237026 km/s from the first reference in BERV: core r is 0.964597 barycentric versus 0.983516 topocentric, and surrounding-pattern r is 0.928074 versus 0.945459. The preference is therefore not universal pair by pair. These reused references/exposures are correlated comparisons, not independent detections or binomial trials.

The 59.609813 km/s BERV range is about 22.866247 nominal resolution elements. Crucially, the topocentric center remains the first-discovery anchor, 3869.362264 Å. A barycentric-coherent group center is expected to move by as much as +0.766388 Å relative to that anchor. It lies outside the fixed core in four of seven epochs, including three of the five discovery references. Their topocentric-core correlations compare the fixed anchor neighborhood, potentially other spectral structure; they are not recentered measurements of their own feature. The broad windows retain the displaced feature and its neighbors. All six frozen figures were inspected: the central crest and numerous surrounding structures align closely barycentrically, while the fixed topocentric displays visibly separate them. No fitted lag or width was introduced to produce that agreement.

Native order3 closely follows its same-exposure merged extraction (core r 0.999388–0.999843; surrounding r 0.987953–0.993135). Shared input photons and extraction dependencies make this consistency, not an independent observational confirmation. The three selected order2 exposures retain six signed raw-only profiles because every positive normalization flank is absent. They cover 330–365 grid points; core raw r remains 0.867361–0.954447, but the surrounding comparison has only 279–314 common points, below the required 440. All six surrounding Pearson values and all twelve order2 normalized-RMS values are accordingly unavailable. The available left-flank medians are positive (44.24–98.48 native units); missing right coverage is not a nonpositive-continuum finding. For V2E2-0051/0053, order2 does not cover the original feature center at all and was never selected for measurement.

The preserved raw panels show central extended trace-associated enhancements together with separate compact off-center spots, especially V2E2-0027/order2 and V2E2-0044/order3. Those spots dominate their individual display scales and must not be conflated with the central profile or suppressed to imply photon-only data. No new mapping, subtraction or spatial classifier was applied. Native flux units remain unspecified and merged flux is ADU; normalized comparisons are not calibrated cross-product flux ratios.

The supported conclusion is recurring barycentric spectral morphology with the stated coverage, reference and error-calibration limitations. Stellar, atmospheric, instrumental/reduction, artificial and mixed physical explanations have not been discriminated by a calibrated origin model here. All five U labels and earlier findings remain unchanged. This bounded C003 context is complete, with no further variants proposed; NEXT_STEP.md returns to the predetermined C005 group.

Evidence binding (SHA-256, paths relative to this phase):

- `analysis/results/SUMMARY.json`: `5f4defca69dde18ea5a82d76ee95ef9066ba35a36acb49d99d6c2db0eccc39b2`
- `analysis/results/PROFILE_METRICS.json`: `bef88cc3c6aeda068c0c8e87cd4c3a5b533c177bbe731f5b62379247d29fb42b`
- `analysis/results/COMPARISONS.json`: `2f91315021fe322a1cbc824b6866e12d51bfa4f46a47c938d974bc8eb6fc3d0d`
- `analysis/results/PLOT_INDEX.json`: `a5c20cb7b7a63571c6aa352fe070d96f9d8c07e98b6465c95435f22b015d9cef`
- `analysis/results/PRESERVED_RAW_CONTEXT.json`: `695f905094714142535f39251749e86a8c76fdd913e8acf3ddc5bb52b9f3f665`
