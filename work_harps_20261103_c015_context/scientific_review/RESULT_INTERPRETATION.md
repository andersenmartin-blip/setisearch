# C015 scientific interpretation

The fixed singleton C015 context retains a multi-sample central enhancement and a structured surrounding spectrum across seven existing HD114386 epochs. All six other epochs have higher raw Pearson correlation and lower normalized RMS in barycentric coordinates than in the fixed topocentric frame, in both the original core and surroundings. August 2023 has much larger retained differences and noisy scaled variation. **V2E2-0095 remains U.** No line identification, physical-origin assignment, qualified laser candidate, significance estimate or calibrated null follows.

The exact method was public and read back before computation in commit `622447cb88946e3e2f0020dc7dc59c99c081b11b`, PLAN SHA-256 `8f1bab6cd274e703d96d4a707b6ef189fb0ca1c13e5d977ed8d65bd6916fc3a4`. The single released run retains 16 profiles and 32 comparisons, including four identical-product self rows, eight bounded source windows and one byte-exact historical raw-panel copy. All 32 Pearson and 32 normalized RMS values are evaluable. Every profile has complete raw/normalized grid support, a valid positive two-flank reference and a false low-reference flag; none is raw-only, blocked or structurally excluded. Self rows and same-exposure native/merged comparisons add no independent observing evidence.

## All six other epochs against one May reference

Each range covers all six other epochs against the fixed May 16, 2022 discovery, excluding its self rows. The single reference and original catalog core replace the preceding C016 joint midpoint and four-reference design.

| Frame | Region | Raw Pearson r range | Median raw r | Normalized RMS range |
|---|---|---:|---:|---:|
| barycentric | Original core | 0.827496–0.985659 | 0.974091 | 0.124497–0.641368 |
| barycentric | Surroundings | 0.785728–0.975927 | 0.967418 | 0.105893–0.347069 |
| topocentric | Original core | -0.433032–0.123852 | -0.338000 | 0.697342–1.017536 |
| topocentric | Surroundings | 0.056682–0.215856 | 0.119729 | 0.605490–0.712009 |

August 27, 2023 has the lowest barycentric r and largest RMS in both regions: core r 0.827496 / RMS 0.641368, surrounding r 0.785728 / RMS 0.347069. It remains in every table and figure. March 7, 2022 has the highest barycentric r in both regions, 0.985659 core and 0.975927 surrounding, and the lowest surrounding RMS, 0.105893. April 29, 2023 has the lowest core RMS, 0.124497. No favorable epoch, reference or alternate normalization was selected.

The topocentric core correlations are negative in five of six other epochs; January 6, 2022 is the positive case at 0.123852. All topocentric surrounding correlations are positive but low, 0.056682–0.215856. These outcomes concern the fixed windows and are not calibrated physical-origin tests. Three metadata-predicted coherent centers lie outside the fixed topocentric core, so some core comparisons can describe neighboring structure rather than the catalog feature's center.

The broad figure shows repeated crests and troughs across the six-Angstrom interval, especially on the negative-offset side and around the central complex. The core figure retains the broad central rise, a positive-side depression and a neighboring rise toward its right edge. Raw amplitudes vary substantially. August is weakest in raw ADU but develops a higher, jagged scaled crest and extra broad-window spikes after division by its lower fixed reference. Neither the central crest nor surrounding agreement isolates a physical emission line or measures its linewidth. No center, width, lag, stellar velocity, continuum, background or drift was fitted.

## Signed originals and fixed reference levels

All 16 profiles retain 601 finite raw and normalized grid centers. All comparisons use the full 51 core or 550 surrounding centers, above the frozen support minima 41/440. There are no gap or outside-coverage masks. Full interpolation support and a positive pooled reference do not require all individual signed source samples to be positive.

Only the January 2, 2023 merged exposure has a nonpositive original source sample in this bounded window: **1/600 (0.1667%)** in each frame, lying in the positive reference flank, **1/150 (0.6667%)**. Its negative flank has none. These are two frame views of one observation, not two independent exposures. The remaining fourteen profile rows have zero nonpositive window or flank samples. Every signed original is retained without clipping, flipping or removal.

Each merged frame window has 600 finite originals and 150/150 finite left/right flank samples. The May native order-3 window has 550 finite originals and 135/140 flank samples in each frame, all positive. These original-source counts differ from the 601 interpolated grid centers and from saved bounded windows that also include interpolation brackets. No missing sample is repaired by a new fit.

Merged pooled references span 51.076479–209.268715 ADU and descriptive first-difference proxies span 12.592721–22.729737 ADU. August has the smallest reference, 51.076479 barycentric / 51.918961 topocentric ADU, with proxies 12.592721 / 12.953106. Its low-reference flags are still false under the declared median ≤ 3 × proxy rule. That flag is a specific descriptive threshold, not a formal SNR, absence-of-systematics or general quality certificate. The retained noisy scaled August profile and larger RMS are not fitted away.

The May discovery merged values are identical in both frames at the displayed precision: left/right medians 242.881737 / 174.416153 ADU, pooled reference 209.268715 and proxy 22.729737, with 150 originals in each flank. Native order 3 has medians 221.543442 / 182.437508, pooled reference 200.031738 and proxy 24.811205 in unspecified extracted units. Native BUNIT is absent, and merged ADU is uncalibrated; the extraction scales are not a physical flux ratio or intrinsic brightness measurement.

The fixed flanks contain substantial spectral structure and unequal reference levels. Every signed sample remains in the pooled median. These are descriptive reference levels, not established line-free continua or fitted backgrounds. Positive scalar division leaves Pearson unchanged; normalized heights and RMS depend on the reference levels. No mask, moved flank, fitted continuum or alternative divisor was tried.

All 16 profiles have zero finite positive ERR samples. Complete support, valid positive references and false low flags do not supply formal uncertainties, significance, false-alarm probability, calibrated sensitivity or a qualified survey null. The first-difference proxies remain descriptive in structured, potentially correlated spectra.

## Sole native order and complete raw context

Fresh checks of all 72 native order headers select **order 3 alone**, with full contexts, original cores and both reference flanks in both frames. Order 2 ends 0.047010202 Å below the original May topocentric event center, so it is not a covering native context. This is a center-based scope decision, not a quality-based removal or a transferred order-2 failure from another target.

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 3 | 0.999421 / 0.999421 | 0.988709 / 0.988719 | 0.037485 / 0.037484 | 0.074336 / 0.074308 |

The native figure retains the complete signed and scaled profile and visible small extraction differences. The close agreement uses the same May exposure and extraction lineage as the merged product; it supplies no additional independent detection, calibrated physical flux ratio or proof of raw registration.

The complete historical raw/excess pair shows a central vertical band and a broad diffuse central enhancement, together with strong alternating positive and negative right-edge residual lobes. Both central and edge structures remain visible at the fixed full scales. The edge structure is not assigned to the catalog feature. Every saved pixel and the historical subtraction remain exact. No crop, contrast variant, new registration, spatial model, background fit or pixel statistic was introduced. This is descriptive morphology, not a physical-origin classification.

Original order 3 retains true global-grid, local usable, baseline verified and later five-window support. These stages remain separate from fresh geometry and flux quality. All historical primary, secondary and adopted reviews remain **U/U/U**, describing a multi-sample native peak and diffuse trace-associated excess without a distinct charge track. Mapping support and native/merged similarity do not change that label or qualify a laser candidate.

## Own May anchor and three outside-center predictions

The exact original scientific center is **3869.915 Å**, with original core **[3869.665,3870.165] Å** and context **[3866.915,3872.915] Å**. This is the singleton's original catalog-centered interval, without C016's shifted common midpoint or member-core boundary differences. Its sole catalog/discovery marker is zero in both frames. Catalog/template width is not a measured physical linewidth.

The reference is ADP.2022-05-17T01:02:16.724, observed May 16, 2022, BERV **−10.767337430651 km/s**, giving wavelength-specific topocentric-air anchor **3870.0539967497375 Å**. The seven existing HD114386 January 2022–August 2023 epochs span **51.572001697156 km/s** in BERV. The May product is one of C016's former discovery references, but its March common anchor and four-reference accounting do not apply here.

Three metadata-predicted coherent centers lie outside the fixed ±0.25 Å topocentric core, on its negative side: January 6, 2022 −0.484329367 Å; March 7, 2022 −0.386319562 Å; January 2, 2023 −0.476711859 Å. Four remain inside: May 16 zero; April 29, 2023 −0.100042176 Å; July 1 +0.181391100 Å; August 27 +0.147900782 Å. These coordinates are not fitted peaks and do not establish full support for an extended feature. The fixed core can retain part of displaced structure or neighboring features. No anchor or boundary was moved.

C015 reuses all seven HD114386 observations and original 0095 epoch/profile/raw evidence. Its window and native order 3 are disjoint from C016's order-19 window and completed blue normalization windows for 0092/0104. Numeric overlap with older HD106515A/HD112410 contexts shares no source pixels or observing products because those are other targets. There is no blind, untouched, independent-data, archive-completeness or added-observing-time claim.

## Verification and staged next-group history

All four figures were visually inspected at original resolution, including seven-epoch legends, signed/scaled variation, the native row and the entire raw/excess pair. All 35 numerical output hashes remain exact. Independent reconstruction passes **455 checks across 63,724 scalar values**, verifying all eight source windows, sixteen profiles, 32 comparisons, one exact raw copy, four self rows and all 56 frozen sources without importing production functions. This establishes computational consistency, not human peer review or physical-origin validation.

The next first unfinished original queue route was fixed before C015 values: **C018 / R019**, starting at row 33, JOINT_PROFILE_CONTEXT on **HD114783**. Keep all seven members 0114/0119/0124/0128/0133/0134/0138 at rows 33/38/42/46/50/51/54, their own seven January 2022–July 2023 observations and all seven discovery references, BERV span 59.073251754930496 km/s. Proposed midpoint 3869.33375 Å and first-January anchor 3868.9509913064876 Å require a fresh inventory and separate public freeze. Forty-two directed nonself rows per frame/region would repeat twenty-one unordered pairs over only seven observations.

Do not flatten the next group's history. Six batch03 members have original U/U/U reviews; **0128 instead has original primary I, secondary M normalized to I, and adopted baseline I**, followed by a completed unchanged-coordinate five-window diagnosis, later U/U reviews and current adopted U. All original order-2 contexts retain true global support but false local/baseline verification; order 3 retains true original stages, with later five-window support separately true for both. Later support does not rewrite original failures or establish physical origin. The remote bright pixel in the 0134 review does not classify its central diffuse feature. Exact source paths, stages and hashes remain in the fixed handoff.

Completed C013/C014 normalization routes and the prior 0128 mapping diagnostic are not replayed. Current C016 member rows remain one completed joint task, and C015 is now complete without changing U. No C018 array analysis, acquisition or replay of completed work was executed here.
