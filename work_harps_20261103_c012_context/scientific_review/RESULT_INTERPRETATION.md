# C012 scientific interpretation

The fixed C012 context retains a central multi-sample enhancement within a strongly structured surrounding spectrum. All six nonself HD112410 epochs have higher raw Pearson correlation and lower normalized RMS in barycentric coordinates than in the fixed topocentric frame, in both the original core and surroundings. The shapes and scaled heights retain visible variation. **V2E2-0087 remains U**. These descriptive comparisons identify neither a spectral line nor a physical origin, qualified laser candidate or calibrated null.

The exact method was public and read back before computation in commit `3815808d874c9cf927da83dc287631e18de3bdd4`, PLAN SHA-256 `247b79d76ef2129f4cf369ec6dd5e188d25a827c7c2d6f627d560942cd087aee`. The single released calculation retains 18 measured profile slots and 36 comparison slots, including four identical-product self rows, nine bounded source windows and two exact historical raw-panel copies. Two native profile rows are deliberately raw-only; no source read is blocked and no covering order is structurally excluded. Of 36 retained comparisons, 34 Pearson values and 32 normalized RMS values are evaluable. Missing values and their reasons remain in the ledger. Self rows and native/merged comparisons add no observing evidence independent of their shared exposure.

## Complete epoch comparison and variation

Each range covers all six other epochs against the fixed April 29 discovery, excluding self rows.

| Frame | Region | Raw Pearson r range | Median raw r | Normalized RMS range |
|---|---|---:|---:|---:|
| barycentric | Original core | 0.912614–0.963934 | 0.947228 | 0.096448–0.135848 |
| barycentric | Surrounding pattern | 0.952137–0.981032 | 0.970949 | 0.110198–0.186254 |
| topocentric | Original core | -0.417189–-0.156073 | -0.358147 | 0.425499–0.540419 |
| topocentric | Surrounding pattern | -0.105845–0.098558 | -0.035499 | 0.728194–0.799174 |

May 28 has the lowest barycentric correlation and largest barycentric RMS in both regions: core r 0.912614 / RMS 0.135848 and surrounding r 0.952137 / RMS 0.186254. The highest barycentric core r is June 22, 0.963934; the highest surrounding r is May 30, 0.981032. July 9 has the lowest barycentric core RMS, 0.096448. Every epoch remains in the figures and tables, with no alternate reference or quality-based removal.

The broad figure shows repeated crests, troughs and unequal shoulders throughout the fixed six-Angstrom interval. Much of the surrounding pattern aligns barycentrically, while its fixed topocentric representation separates those structures. The core figure retains a broad, asymmetric central crest in the discovery and corresponding multi-sample crests in later epochs; the weaker May 28 raw spectrum and noisier scaled shape remain visible. Neither the surrounding agreement nor the catalog-centered crest isolates a physical emission line or measures a linewidth. No free lag, radial velocity, drift, width, continuum or background was fitted.

## Signed source samples and fixed reference levels

All 14 merged profiles and both order 3 frame rows retain all 601 raw and normalized grid centers, with usable positive two-flank references and false low-reference flags. The two order 2 rows retain 378 raw centers and zero normalized centers, with `MISSING_RIGHT_FLANK_COVERAGE`, null valid reference and null low-reference flags. The nominal grid is not reduced to the available order 2 support. All 18 rows have zero finite positive ERR samples; the stored first-difference proxies are descriptive and supply no formal uncertainty model.

Nonpositive signed originals remain explicit. May 28 is the only merged exposure with such samples in this bounded window: 3/600 originals (0.5%) in both frames, all in the negative flank, 3/150 (2%). Its positive flank has none. The other merged rows contain zero nonpositive originals, including the discovery. June 22 has 599 finite original source samples and 149/150 left/right flank samples topocentrically; the remaining merged rows have 600 originals and 150/150 flank samples. These original-sample counts differ from the complete 601-point interpolation grid.

Order 2 retains 2/423 nonpositive source-window originals (0.4728%) in each frame, including 1/166 (0.6024%) in its available negative flank; the positive-flank count is zero because that flank is absent. Order 3 retains zero nonpositive originals among 546, with 134/139 finite left/right flank samples. No signed value was clipped, flipped or omitted.

The merged pooled references span 92.346405–332.728928 ADU, and their first-difference proxies span 16.634240–25.463589 ADU. May 28 has the smallest reference: 92.346405 barycentric / 99.829357 topocentric ADU. Division by these lower levels preserves a noisier scaled shape; it is not a calibrated physical emission-strength measurement. False low flags mean only that the declared positive-reference threshold relative to the descriptive proxy was not met.

The discovery merged left/right medians are 411.437912 / 293.835861 ADU, pooled reference 332.728928 and proxy 25.463589. Order 3 has left/right medians 353.979523 / 297.636047, pooled reference 311.214966 and proxy 29.717274 in unspecified native extracted units. Order 2's available negative-flank median is 89.043491, with a left-flank proxy 18.619317, but this available median is **not a valid two-flank reference** and was never used as a replacement divisor. Native BUNIT is absent, merged ADU is uncalibrated, and the differing extracted scales are not physical flux ratios.

The negative reference interval contains several prominent crests and troughs, while the positive interval samples a different structured level. Every fixed-flank sample remains. The pooled medians are descriptive reference levels, not established line-free continua or fitted backgrounds. Positive scalar division leaves Pearson unchanged; heights and normalized RMS depend on the declared reference levels.

## Partial native coverage and preserved raw context

A fresh scan of all 72 native order headers selects orders 2 and 3 alone. Order 2's positive endpoint lies at only +0.776414 Å barycentric / +0.776405 Å topocentric relative to the fixed centers, before the reference flank starts at +1.5 Å. It has full 51-point core coverage, where its raw native/merged correlations are 0.730305 barycentric / 0.730332 topocentric. Its surrounding raw support is only 327/550, below the frozen 440-point gate, so both broad Pearson values are absent. All four order 2 normalized RMS values are absent because no valid two-flank divisor exists. The raw-only rows, available signed shape and explicit reasons are retained instead of discarding the order or moving a flank.

Order 3 covers both complete contexts and flanks. Native/merged core r is 0.998642 in both frames, with RMS 0.034083 barycentric / 0.034084 topocentric at six decimals. Surrounding r is 0.988140 barycentric / 0.988143 topocentric, RMS 0.088252 / 0.088239. Its native figure follows the discovery's structured spectrum, with visible extraction differences. This strong similarity uses the same exposure and extraction lineage; it is not a second independent detection or validation of raw registration.

Both complete historical raw/excess pairs were visually inspected at their fixed full scales. Order 2 shows noisy, low-contrast central diffuse enhancement; order 3 shows a clearer central vertical band and diffuse central excess patch. Strong alternating right-edge pixels and positive/negative residual structure remain visible, especially in order 3. No crop, contrast variant, new registration, subtraction, spatial model or pixel statistic was introduced. Visual morphology here is descriptive.

Original order 2 global-grid and later five-window mapping support are true, while original local mapping and baseline verification are false. Order 3 retains true at every stage. These are separate historical diagnostics. Later support, header coverage and extraction agreement cannot repair the original order 2 local/baseline limitations. Primary, secondary and adopted reviews all retain **U** for broad enhancement shared by orders 2/3, noisier order 2, smoother order 3 and trace-associated structure; no physical-origin reassignment follows.

## Fixed-frame geometry and dependence

The exact catalog center is 3869.2675 Å. The April 29 discovery, BERV 3.40485846065643 km/s, defines the new wavelength-specific topocentric-air anchor 3869.2235557371996 Å. The seven existing April–August 2025 epochs span 21.30284860830273 km/s in BERV. No C010 numeric anchor or HD106515A products/reference/span were transferred.

Only August 7 has its metadata-predicted barycentrically coherent center outside the fixed ±0.25 Å topocentric core: +0.274958234 Å, 0.024958234 Å beyond its positive edge. July 9 remains inside at +0.240601520 Å, only 0.009398480 Å from that edge. These are coordinate predictions, not fitted peaks. Center inside/outside status does not express a finite-width structure's full support; the fixed comparison can include part of a displaced feature or neighboring structure. No recentering or physical-origin inference was introduced.

C012's bounded window is disjoint from C010, although all seven HD112410 observations are reused. Numeric overlaps with older HD106515A C002/C003/C004 blue windows share no pixels or observations because the target and products differ. Original 0087 epoch/profile and raw evidence already existed. This adds no observing time, blind or independent new-observation claim, archive completeness, calibrated significance, false-alarm probability, sensitivity estimate or qualified survey null. The catalog template width is not a measured physical linewidth.

## Verification and fixed handoff

All four complete figures were visually reviewed, including seven-epoch legends, shared merged scales, signed nonpositive values, both native rows, raw-only annotations and both complete raw/excess pairs. All 39 numerical output hashes remain exact. Independent reconstruction passes 481 checks across 70,371 scalar values and all 49 frozen method/input sources, without importing production functions. This establishes computational consistency, not human peer review or physical-origin validation.

The next original remaining queue item was fixed before C012 values: **row 25, C011 / R012 / V2E2-0089**, exact center 3865.6775000000002 Å on HD112410. It uses the same seven epochs but its own May 28 discovery, ADP.2025-05-29T01:01:14.389, BERV −5.48386283255014 km/s, giving anchor 3865.748213029564 Å. Its core lies outside C012's bounded window, while the broader same-target windows overlap by 2.4100000000003092 Å. Both C011 historical orders 2/3 have all mapping stages true and U/U/U. Fresh inventory and a public method freeze are required before future values. No C011 analysis was executed here.
