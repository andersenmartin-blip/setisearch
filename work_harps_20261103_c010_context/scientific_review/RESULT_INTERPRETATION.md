# C010 scientific interpretation

The fixed C010 context shows a broad, multi-sample central enhancement and surrounding structured spectrum that agree better in barycentric coordinates across the seven existing HD112410 epochs. All six nonself epoch comparisons have higher barycentric raw Pearson correlation and lower barycentric normalized RMS in both the original core and surroundings. The shapes and scaled heights vary substantially. **V2E2-0086 remains U**, with no line identity, physical-origin assignment, qualified laser candidate or calibrated null result.

This is HD112410's own April–August 2025 cohort, not the preceding HD106515A products. The method was public and read back before computation in commit `acb3a382b43ca0b9d3d13f3e30317383f591fb10`, with PLAN SHA-256 `a17103d238df587dfdf45d61d3b6500971dc6e8066f0e6b738bde4720c5b04e9`. The single released calculation retains 16 measured profiles and 32 comparisons, including four identical-product self rows, eight bounded source windows and one exact historical raw-panel copy. All statistics are numerically evaluable; no profile is raw-only, blocked or structurally excluded. Self rows and same-exposure extraction comparisons add no independent observing evidence.

## Complete comparison and retained variation

Each range below covers the six other epochs against the fixed April 2025 discovery, excluding self rows.

| Frame | Region | Raw Pearson r range | Median raw r | Normalized RMS range |
|---|---|---:|---:|---:|
| barycentric | Original core | 0.596420–0.869229 | 0.750154 | 0.495566–1.600996 |
| barycentric | Surrounding pattern | 0.836596–0.962802 | 0.899448 | 0.225915–0.675335 |
| topocentric | Original core | -0.130725–0.323374 | 0.027023 | 1.155767–1.811756 |
| topocentric | Surrounding pattern | 0.446920–0.583838 | 0.455775 | 0.752227–0.921135 |

**May 28 has the largest barycentric RMS in both regions**, 1.600996 core and 0.675335 surrounding. June 27 has the lowest barycentric core r, 0.596420; May 28 is also weak at 0.597206. May 30 has the highest barycentric r in both regions, 0.869229 and 0.962802. All epochs remain in the tables and figures, without quality-based removal or a replacement reference.

The core plot retains the discovery's broad central crest, different shoulders and depressions in the other epochs, and substantial scaled-height variation. The broader window contains a complex central pattern and deep troughs near −1.7 and +2.4 Å. Those broad structures contribute to the surrounding correlation; their agreement does not isolate a physical emission line or measure its linewidth. The fixed calculation supplies descriptive morphology rather than a fitted line model or calibrated frame-origin test.

## Signed samples and reference levels

All 16 profiles have the complete 601-point raw and normalized grid, valid positive two-flank references and false low-reference flags. Every comparison uses all 51 core or 550 surrounding points, above the frozen support minima of 41/440. Every profile has zero finite positive ERR samples. Full support and a positive pooled reference do not imply that individual signed samples are positive or that calibrated uncertainties exist.

**Every one of the 16 profile rows contains nonpositive original source samples.** The 14 merged frame rows retain between 2 and 21 nonpositive samples among 600 finite originals, 0.3333–3.5%. These rows represent seven observations, with paired frames; they are not fourteen independent observations. May 28 has the largest fraction, 21/600 in both frames. Its left flank has 12/150 nonpositive samples barycentrically and 11/150 topocentrically, while its right flank has 8/150 in both. The discovery merged window retains 2/600 in both frames, all in its negative flank (2/150). The complete per-frame fractions for the remaining observations are retained in the profile metrics and report. No signed value was clipped, flipped or omitted.

Both native frame rows retain 3 nonpositive samples among 562 finite source-window originals (0.5338%); their left flank has 3/139 (2.1583%) and right flank 0/143. These original-sample denominators differ from the 601 interpolated grid centers. All valid references still pass the fixed two-flank support and positivity gates. The false low flags apply to the declared reference ≤ 3 × first-difference-proxy rule, not a general absence-of-systematics or formal SNR judgment.

Merged references span 59.985079–219.432755 ADU, and descriptive first-difference proxies span 16.159889–23.525127 ADU. The May 28 reference is the smallest, 59.985079 barycentric / 62.785772 topocentric ADU. Its weak signed raw spectrum becomes a relatively high and jagged scaled profile after division by those fixed levels. This scaling cannot be read as a calibrated emission strength or intrinsic brightness change. Exposure flux and reference differences are retained rather than fitted away.

The discovery merged values are the same in both frames: left/right medians 192.890640 / 278.714310 ADU, pooled reference 219.432755 ADU and proxy 23.324425 ADU, with 150 finite originals in each flank. Native order 1 has 139/143 finite flank samples, medians 180.737869 / 295.197479, pooled reference 216.662064 and proxy 25.384953 in unspecified extracted units. Native BUNIT is absent, and its scale is distinct from merged ADU; no physical flux ratio follows.

The two deep outer troughs fall inside the fixed reference intervals [−3,−1.5] and [+1.5,+3] Å. All of this structure and the nonpositive samples remain in the pooled medians. These are descriptive reference levels, not established line-free continua or fitted backgrounds. Positive scalar division leaves Pearson unchanged, while plotted heights and normalized RMS depend on the chosen levels. No mask, alternate flank, fitted continuum, clipping or new normalization was tried.

## Native extraction, raw panel and registration limits

Fresh checks of all 72 native order headers identify order 1 alone covering the original center, with complete contexts and flanks in both frames. Native-to-merged core r is 0.999254 in both frames, with RMS 0.052452. Surrounding r is 0.995881 in both frames at six decimals, with RMS 0.085030 barycentric / 0.085032 topocentric. The native figure preserves the broad central crest, neighboring structure, signed values and small extraction differences. These products share one observation and extraction lineage and therefore supply no second observing detection.

Unlike the preceding C009 full panel, the C010 raw cutout has a prominent central vertical band and broad bright patch. The unchanged excess map retains diffuse positive and negative residual lobes. Weaker right-edge structure remains visible but does not dominate the full scale. The complete raw/excess pair was retained without a new crop, contrast variant, pixel statistic, registration, subtraction or spatial model. This visual description is not a physical-origin classification.

**Original order 1 local mapping and baseline verification are false**, alongside true global-grid and later five-window reference diagnostics. All four stages remain separate. Header coverage, strong native/merged similarity and later reference-window support cannot retroactively repair the original local/baseline registration limits. Primary, secondary and root adoption all remain **U** for broad diffuse trace-confined structure without an unambiguous compact charge deposit. The stored panel and all original review texts remain exact; no new origin assignment follows.

## Fixed frame, near-edge geometry and dependence

The exact scientific center is 3823.0649999999996 Å. The discovery on 2025-04-29, BERV 3.40485846065643 km/s, defines the wavelength-specific fixed topocentric-air anchor 3823.0215804708346 Å. Its seven target-specific epochs span 21.30284860830273 km/s in BERV. No prior target's products, reference, numeric anchor or 59.6098 km/s span was inherited.

Only August 7 has its metadata-predicted barycentrically coherent center outside the fixed ±0.25 Å topocentric core: +0.271674988 Å, only 0.021674988 Å beyond the positive edge. July 9 is inside at +0.237728523 Å, only 0.012271477 Å from that edge. The other five center predictions are inside. These are coordinate predictions, not fitted peak positions. A center's binary inside/outside status does not describe a finite-width structure's full support. The fixed window can include only part of a shifted feature or neighboring structure; no recentering was introduced and no physical origin follows from frame preference.

The C010 window is disjoint from the previous C001–C009 bounded wavelength windows, and the target changes to HD112410. Original 0086 epoch/profile and raw evidence and all seven HD112410 observations already existed. This adds no observing time, archive completeness, blind or independent new-observation claim. The absent positive ERR support and descriptive noise proxies provide no formal uncertainty model, significance, false-alarm probability, sensitivity estimate or qualified survey null. The catalog template width was not measured as a physical linewidth.

## Verification and handoff

All four figures were visually inspected, including full titles and seven-epoch legends, signed negative values, both native views and the complete raw/excess pair. Their full PNG decoding, bytes and hashes match the unchanged plot index. All 47 frozen method/input source bindings and 35 numerical output hashes remain exact. Independent reconstruction passes 432 checks across 63,469 scalar values, without importing production functions. This verifies computational consistency, not human peer review or independent observations.

The next original remaining queue item was frozen before C010 values: **row 24, C012 / V2E2-0087**, on HD112410 at 3869.2675 Å, preceding C011 at row 25. It reuses the same seven observations and April discovery but requires its own wavelength-specific anchor and fresh covering-order inventory. Historical order 2 local/baseline failures and order 3 supported stages remain separate. Its numeric blue-wavelength overlaps with older HD106515A windows share no pixels because those are different target observations. No C012 analysis was executed here.
