# C011 scientific interpretation

The fixed C011 context retains a broad multi-sample central crest within a strongly structured spectrum. All six nonself HD112410 epochs have higher raw Pearson correlation and lower normalized RMS in barycentric coordinates than in the fixed topocentric frame, in both the original core and surroundings. Shape, amplitude and reference-level differences remain. **V2E2-0089 remains U.** No line identification, physical-origin assignment, qualified laser candidate, significance estimate or calibrated null follows.

The exact method was public and read back before computation in commit `dad9f542b6f7bb830f1020d373634012483e7b15`, PLAN SHA-256 `95aafe1f5985cdb57a112f787bfd3f999ff1cccf310905e85c25eb97fb4691a0`. The single released run retains 18 measured profiles and 36 comparisons, including four identical-product self rows, nine bounded source windows and two exact historical raw-panel copies. Every profile has complete raw and normalized grid support and a valid positive two-flank reference. All 36 Pearson and 36 RMS values are evaluable; no profile is raw-only, blocked or structurally excluded. Native order 2 nevertheless has true low-reference flags in both frames, retained in the metrics and figures. Self rows and same-exposure native/merged comparisons add no independent observing evidence.

## All six other epochs and retained variation

Each range covers the six other epochs against the fixed May 28 discovery, excluding self rows. April 29 is an ordinary nonself epoch in this analysis.

| Frame | Region | Raw Pearson r range | Median raw r | Normalized RMS range |
|---|---|---:|---:|---:|
| barycentric | Original core | 0.949081–0.973576 | 0.963708 | 0.117274–0.162986 |
| barycentric | Surrounding pattern | 0.961697–0.969492 | 0.964388 | 0.111964–0.129754 |
| topocentric | Original core | -0.711186–0.953127 | -0.313622 | 0.159233–0.967655 |
| topocentric | Surrounding pattern | -0.017720–0.954910 | 0.164278 | 0.138355–0.649004 |

June 27 has the lowest barycentric core r, 0.949081, and largest core RMS, 0.162986. May 30 has the highest barycentric core r, 0.973576. April 29 has the strongest barycentric surrounding correlation, 0.969492, and smallest RMS in both regions, 0.117274 core / 0.111964 surrounding. July 9 has the lowest barycentric surrounding r, 0.961697; August 7 has its largest surrounding RMS, 0.129754. No epoch or reference was replaced to improve agreement.

May 30 is an informative near-reference case: its predicted topocentric center is only +0.007535802 Å from the fixed May 28 anchor. Its topocentric core correlation remains high, 0.953127, compared with 0.973576 barycentric; its surrounding values are 0.954910 topocentric and 0.965899 barycentric. Barycentric RMS is still lower in both regions. The other five topocentric core correlations are negative. This variation is preserved rather than turning frame preference into a binary origin classifier.

The core figure retains a broad asymmetric central crest, shoulders on its negative-offset side, a positive-offset depression and neighboring rising structure. April 29 is strongest in raw ADU, while the May discovery has a lower raw scale and a noisier scaled crest. The broad figure shows repeated peaks and troughs throughout both reference intervals; these surrounding structures contribute to correlation. Neither their agreement nor the central crest isolates a physical emission line or measures a linewidth. No center, width, lag, stellar velocity, drift, continuum or background was fitted.

## Valid normalization with low native reference

All 18 profiles retain all 601 raw and normalized grid centers. All comparisons use the full 51 core or 550 surrounding centers, above fixed minima 41/440. There are no outside-coverage or gap masks. The 14 merged rows and both order 3 rows have false low-reference flags; **both order 2 rows have true low-reference flags**. These true flags coexist with valid positive references and complete support. They are not missing-flank or raw-only failures.

The order 2 pooled reference is 43.386597 in unspecified native extracted units, with first-difference proxy 17.929966: its positive median satisfies the declared reference ≤ 3 × proxy rule. Both flanks are present, with 160/168 finite original samples and left/right medians 69.415939 / 27.218124. Its scaled curve is visibly jagged, especially toward its lower positive-flank level. Division amplifies the displayed flux variation and noise together; it does not change Pearson under positive scalar scaling. The descriptive flag is not a formal SNR or a physical-origin judgment, and no mask, alternate divisor, fitted continuum or flank substitution was introduced.

The May discovery merged reference is 155.309959 ADU, proxy 21.505817, left/right medians 170.531380 / 122.730335 and finite flank counts 150/150, with false low flags. Order 3 has reference 109.767494, proxy 19.468108, medians 112.543205 / 108.302868 and 132/136 finite flank samples, also with false low flags. A merged-spectrum flag does not certify that every overlapping native order has a strong reference. Native BUNIT is absent; the native extracted scales are unspecified and distinct from uncalibrated merged ADU, so no physical flux ratio or intrinsic brightness change follows.

Merged references span 155.309959–553.642212 ADU and their descriptive proxies span 19.663567–36.705803 ADU. Both reference flanks contain structured spectra at unequal levels. All samples remain in the pooled medians. These medians are descriptive reference levels, not established line-free continua or fitted backgrounds. Scaled heights and normalized RMS depend on them.

## Signed originals and unavailable uncertainty

Six profile rows contain nonpositive signed original samples. The May discovery merged window has 3/600 originals (0.5%) in each frame, with zero nonpositive samples in either reference flank. Order 2 has 29/655 window originals (4.4275%) in each frame, including 13/168 in its positive flank (7.7381%) and zero in its negative flank. Order 3 has 3/534 window originals (0.5618%) in each frame, again zero in either flank. The other twelve merged frame rows contain no nonpositive window originals. These paired frame rows reuse observations; they are not independent exposures. No signed value was clipped, flipped or omitted.

May 30 has 599 finite original window samples and 149/150 left/right flank samples topocentrically, compared with 600 and 150/150 barycentrically. Its interpolated raw and normalized grids still have all 601 centers without gaps or outside coverage. Original source masks, interpolation brackets and interpolated grid support have different denominators; this is not a missing value repaired by a new fit.

All 18 profiles have zero finite positive ERR samples. Complete support, valid positive references and false low flags in some rows do not supply calibrated uncertainties, significance, false-alarm probability, sensitivity or a qualified survey null. The first-difference proxies remain descriptive in structured and potentially correlated spectra.

## Both native orders and preserved raw morphology

Fresh checks of all 72 native order headers select orders 2 and 3 alone, both covering complete cores, contexts and reference flanks in both frames. Unlike C012's April order 2 context, this May order 2 context has full wavelength coverage and valid normalization; its separate low flag is an observed reference-quality outcome.

Native order 2 core correlations are 0.918410 barycentric / 0.918409 topocentric, with RMS 0.216693 / 0.216697. Surrounding r is 0.804246 / 0.804243, RMS 0.458426 / 0.458443. Order 3 core r is 0.991103 in both frames, RMS 0.143153 / 0.143152; surrounding r is 0.924009 / 0.923999, RMS 0.200610 / 0.200626. The native figure retains the noisier low-reference order 2, smoother order 3 and visible extraction/scale differences. Both products share the May discovery exposure and extraction lineage with the merged spectrum, so these comparisons are dependent and do not supply another observing detection.

Both complete historical raw/excess pairs were inspected at their frozen full scales. A diffuse central enhancement appears in noisy order 2 and more clearly in order 3, with a vertical band and residual structure. Strong alternating positive and negative right-edge features remain visible, especially in order 3. They are retained without assigning them to the catalog feature. No new crop, contrast variant, registration, subtraction, spatial model or pixel statistic was introduced. These images do not establish physical origin.

All four original mapping stages—global grid, local usable, baseline verified and later five-window support—remain true for both C011 orders. This differs from C012's original order 2 local/baseline failures. Fresh coverage, historical registration support and spectral quality are separate diagnostics. Primary, secondary and adopted reviews all retain **U/U/U** for broad native structure and diffuse trace-associated enhancement. Neither extraction agreement nor mapping support silently changes that disposition.

## Own May anchor and known shared flux

The exact scientific center is 3865.6775000000002 Å. The discovery is ADP.2025-05-29T01:01:14.389, observed May 28 2025, BERV −5.48386283255014 km/s, defining its own wavelength-specific topocentric-air anchor 3865.748213029564 Å. The seven existing April–August HD112410 observations span 21.30284860830273 km/s in BERV. The April discovery reference and numerical anchor from C012 were not transferred.

**All seven metadata-predicted coherent centers remain inside the fixed ±0.25 Å topocentric core.** April 29 is −0.114616520 Å from the anchor; August 7 is +0.160086601 Å, still 0.089913399 Å inside its positive boundary. These coordinate predictions are not measured peaks and do not prove full support for an extended feature. No C012 August-outside caveat applies, and no recentering was introduced. Fixed windows can still describe neighboring structure.

The broader C011/C012 windows overlap [3866.2675,3868.6775000000002] Å, width 2.4100000000003092 Å, on the same seven merged products. C011's original core lies outside the prior C012 window, but its surrounding/reference pixels were partly viewed there already. C010's window is disjoint. Numeric overlaps with older HD106515A windows share no source pixels or observing products. Original 0089 epoch/profile/raw evidence also already existed. There is no blind, untouched, independent-data, new observing-time or archive-completeness claim. The catalog template width is not a measured physical linewidth.

## Verification and first unfinished route

All four complete figures were visually reviewed, including all seven-epoch legends, shared merged frame scales, signed nonpositive values, both native low-flag annotations and both full raw/excess pairs. All 39 numerical output hashes remain exact. Independent reconstruction passes 481 checks across 71,203 scalar values, verifying all 50 frozen sources and full released scope without importing production functions. Computational consistency does not constitute human peer review or physical-origin validation.

The next unfinished original queue route was frozen before C011 values: **row 27 C016 / R017, JOINT_PROFILE_CONTEXT**, retaining V2E2-0094/0096/0098/0110 at rows 27/29/30/32. This changes target to HD114386 and uses its own seven 2022–2023 epochs, BERV span 51.572001697156 km/s and four distinct discovery products. The prospective common midpoint is 4303.7875 Å; the first queue discovery provides one common fixed topocentric anchor, while all four references and exact individual centers remain explicit. Each historical order-19 context has all mapping stages true and U/U/U. A fresh inventory and separate public method freeze must precede future values.

The intervening C013/0092 row 26 and C014/0104 row 31 NORMALIZATION_CONTEXT routes are already complete in normalization_context_20261102, with 28 preserved profiles, eight focused windows and 12 native/raw contexts. Their physical origins remain U, but that does not make the completed diagnostic unfinished. Those routes are explicitly skipped using bound completion evidence; they are not replayed as new progress. No C016, C013 or C014 analysis was executed here.
