# C004 scientific interpretation

The fixed C004 context shows closely aligned barycentric spectral structure across all seven reused HD106515A epochs, both inside the original core and across the surrounding ±3 Å window. Under the declared, unshifted descriptive measures, every nonself merged comparison has higher raw Pearson correlation and lower normalized RMS in the barycentric frame than in the one fixed topocentric frame. This is context for the three existing U records 0028, 0045 and 0052; it does not assign physical origin or establish a calibrated technosignature test.

The exact public method was released at commit `7c3e46e41fc98073c844259ab91350b8363bc63a`, with PLAN SHA-256 `044cabc2adafd835cb4882afb506488752c6f0d91743ca564cc076a0031b1670`. The one-shot result retains 20 profiles, 96 comparison rows, 12 identical-product self rows, ten bounded source windows and three preserved raw panels. There are seven merged epochs and three distinct discovery references, all retained. The 43-file numerical ledger is immutable. The three U dispositions and all earlier analyses remain unchanged.

## Fixed comparisons

The following ranges omit identical-product self rows. Each row summarizes 18 comparisons: six other epochs against each of three fixed discovery products. Reversed discovery pairs and repeated epochs are dependent, so these are not 18 independent experiments.

| Frame | Region | Raw Pearson r range | Normalized RMS range |
|---|---|---:|---:|
| barycentric | Original core | 0.925276–0.990102 | 0.072157–0.213129 |
| barycentric | Surrounding pattern | 0.967167–0.995102 | 0.094143–0.217996 |
| topocentric | Original core | -0.261019–0.748067 | 0.259214–0.717136 |
| topocentric | Surrounding pattern | 0.013010–0.459677 | 0.701397–1.063938 |

All 36 nonself frame-paired comparisons (18 core and 18 surrounding) favor the barycentric context by both descriptive measures. This agreement is present for every fixed reference, without choosing the most favorable discovery. The 12 self rows have numerical r≈1 and RMS=0; they establish no recurrence. The comparatively high topocentric core r=0.748067 occurs twice for the reversed March 2023/May 2023 discovery pair. It is one repeated relationship, and the May discovery's catalog feature is outside the fixed topocentric core. The lowest topocentric core RMS, 0.259214 for July 2023 against May 2023, compares fixed windows with both expected catalog centers outside the core. Neither exception can be interpreted as independent evidence for a common stationary core feature.

## Fixed-anchor limitations

The topocentric anchor is the first C004 discovery, 0028 observed 2022-03-07, BERV 10.77158288517 km/s. Its wavelength is 3872.1058747209718 Å; earlier contexts' January anchor was not reused. The other discovery coordinates are displaced by +0.096952 Å (0045, March 2023) and +0.454410 Å (0052, May 2023). Thus the latter reference's catalog feature falls outside ±0.25 Å, while the comparisons and core plots correctly retain the same fixed window.

Metadata predicts a barycentrically coherent center outside that topocentric core in five of seven epochs. January 2022 is only 0.000111 Å beyond the negative boundary (offset −0.250111 Å), much less than the 0.01 Å comparison grid step. Its binary outside status is a consequence of the frozen mask, not robust physical separation. December 2022 is at −0.253172 Å; May 2022 at +0.383142 Å; May 2023 at +0.454410 Å; July 2023 at +0.516770 Å. These are coordinate predictions from catalog wavelength and BERV, not fitted peak positions. No recentering, linewidth, lag, stellar velocity or drift was fitted. A fixed-core comparison can describe different parts of a structured spectrum; its frame contrast is not a calibrated origin classifier.

## Coverage, reference quality and dependence

All 20 profiles have 601 finite raw and normalized grid samples, with no gaps or outside-coverage samples. Every comparison retains all 51 core or 550 surrounding samples, above the frozen minima 41/440. All two-sided references are positive and pass the declared first-difference low-reference flag; there are no blocked or raw-only profiles. This describes numerical availability, not a detection significance.

The May 2022 merged source window contains one nonpositive sample among 600 source samples in each frame (0.166667%). In the topocentric window it also belongs to the right normalization flank (1/150); it was retained with its sign. Other profile-window nonpositive fractions are zero. Positive finite ERR support is zero throughout; native ERR is unavailable. The first-difference proxy and positive-reference gate do not supply a calibrated uncertainty, false-alarm probability, sensitivity or qualified null.

The flanks have conspicuous spectral structure and unequal left/right levels. The C003 original core union [3869.495, 3870.0075] Å lies inside C004's negative reference flank [3869.245, 3870.745] Å. C004's own original core [3871.995, 3872.495] Å was already visible in C003's positive flank. The windows overlap by 3.50625 Å and reuse the same seven observations. Reference medians are descriptive levels, not established line-free continua; no masking or refitting was introduced. Selection before these C004 computations does not make the evidence blind, untouched or independent of C003.

The three native order 3 contexts track their same-exposure merged products closely in both frames: all 12 native/merged comparisons have r=0.997104–0.999765 and normalized RMS=0.013208–0.084486. Native BUNIT is absent, so its extracted units are unspecified; merged units are ADU. Separate flank division does not establish a physical flux ratio. These are related extractions of the same observations, not independent confirmations. Fresh header coverage and finite arrays do not perform new raw registration. The original global, local, baseline and five-window mapping flags are true for all three records, independently checked against the saved historical mapping, but remain historical diagnostics without an origin determination.

## Full figure review

All four saved figures were inspected: merged broad and core context, all three native order 3 rows and all three original raw/excess pairs. Full PNG dimensions, hashes and decode checks are recorded separately in REPORT_CROSSCHECK.json. The merged plots retain all seven epochs and three discovery identities, common vertical limits per quantity/window and the signed/scaled views. The three barycentric catalog markers coincide by construction; the distinct topocentric markers retain the original discovery coordinates, including the May marker outside the core view. The complete core legend was checked at original resolution.

Visually, the central barycentric feature sits amid an extensive structured spectrum whose main shapes recur across the epochs; the fixed topocentric panels spread that structure in coordinate. Native and merged curves largely overlap after their own fixed scaling. The preserved raw panels show trace-associated, spatially extended central enhancement, with nearby signed residual structure; the May 2023 central excess is less pronounced on its independent full scale. These are retained historical panels, with no new subtraction, localization or detector model. Visual consistency neither upgrades their mapping evidence nor resolves physical origin.

No labels, prior raw reviews, original pipeline outputs or earlier context results were changed. The fixed next queue choice is singleton C002 / V2E2-0033; its metadata and dependencies are documented in NEXT_GROUP_METADATA.json and NEXT_STEP.md. No C002 analysis was executed here. This review checks scientific consistency of the bounded computational context; it is not human peer review or new observing evidence.
