# C002 scientific interpretation

The fixed C002 comparison shows recurrent barycentric spectral structure around 3868.6025 Å in all seven reused HD106515A epochs. Each of the six nonself epoch comparisons has higher raw Pearson correlation and lower normalized RMS in the barycentric frame than in the one fixed topocentric frame, in both the original core and surrounding window. This describes the existing spectral context; **V2E2-0033 remains U**, without a line identity, physical-origin assignment, qualified laser candidate or calibrated null.

The method was published and read back before computation at commit `264a6d5cfd8b0b40780df1f28b65986f50659b2e`, with PLAN SHA-256 `3cfcc7ad2007357edb49c39320d33976d5348ea9a3f03b2d700f6bc4cb3e3efe`. The one-shot result contains 18 measured profile slots and 36 comparisons, including four identical-product self rows, nine bounded source windows and two exact historical raw-panel copies. No source profile is blocked or structurally excluded. Sixteen profiles have valid normalization; both order 2 profiles remain raw-only. Consequently 34 Pearson values and 32 normalized RMS values are evaluable. The 39-file numerical ledger and all prior results remain unchanged.

## Fixed merged comparison

Each range below covers all six other epochs against the one May 2022 discovery product; self rows are excluded. The four self rows have numerical r≈1 and RMS=0 and add no recurrence evidence.

| Frame | Region | Raw Pearson r range | Normalized RMS range |
|---|---|---:|---:|
| barycentric | Original core | 0.938800–0.980641 | 0.137251–0.324748 |
| barycentric | Surrounding pattern | 0.957488–0.986064 | 0.148133–0.337123 |
| topocentric | Original core | -0.173859–0.559801 | 0.706058–1.146790 |
| topocentric | Surrounding pattern | -0.196845–0.282579 | 0.922806–1.139846 |

All 14 merged profiles retain 601 finite raw and normalized grid samples. Every merged comparison uses all 51 core or 550 surrounding points, above the frozen minima 41/440. Both figures show a central crest and neighboring shoulders within a much more extensive structured spectrum. The comparison did not isolate a physical emission line or measure its linewidth. Common wavelength grids, interpolation, shared observing products and selected reference levels constrain the interpretation of the frame contrast.

## Order 2: coverage, normalization and mapping are separate limits

Both native orders cover the original catalog center, but order 2 terminates at fixed offsets +1.160941 Å barycentric and +1.161014 Å topocentric. Thus it retains 417 raw grid points and the complete 51-point core, while the whole positive reference flank is absent. Both order 2 profiles correctly carry `MISSING_RIGHT_FLANK_COVERAGE`; they have zero normalized grid points. Their 366 surrounding points fall below the unchanged 440-point raw-Pearson requirement, so both surrounding correlations remain unavailable. All four order 2 normalized RMS outcomes remain unavailable.

Order 2's available left-flank median is positive, **50.288151 in unspecified native units**, from 165 finite samples; it is not a valid two-sided reference. The first-difference proxy is 16.722303, but the low-reference flag is **null**, not false or a passing quality judgment, because the required reference does not exist. The signed available window has 19 nonpositive samples among 465 (4.0860%), and the left flank 3/165 (1.8182%). These values remain signed. Missing right-flank coverage is distinct from weak or nonpositive measured samples.

Core raw Pearson remains evaluable: order 2 versus its same-exposure merged product gives **0.769809 barycentric / 0.769773 topocentric**. This partial morphological agreement does not supply missing normalization or validate raw-detector registration. Original order 2 `local_mapping_usable=false` and `baseline_mapping_verified=false` remain explicit alongside true global and later five-window diagnostics. No mapping gate was changed or repaired.

Order 3 has full 601-point raw and normalized support in both frames, with positive reference **157.091766**, descriptive proxy **22.275848**, false low-reference flags and zero nonpositive available source-window samples. Its same-exposure core correlations are **0.998692 / 0.998693** and surrounding correlations **0.990287 / 0.990297** (barycentric/topocentric). The corresponding normalized RMS values are **0.037713 / 0.037715** in the core and **0.112303 / 0.112245** in the surroundings. All four historical mapping flags are true for order 3, but these remain historical diagnostics. Native extracted units are unspecified because BUNIT is absent; merged values are ADU. Shared extraction agreement is not independent observing evidence or a physical flux ratio.

## Fixed anchor and prior-window dependence

The sole discovery was observed on 2022-05-07, BERV −18.8907517532076 km/s, defining the single fixed topocentric anchor **3868.846286702511 Å**. Earlier March and January anchors were not reused. A barycentrically coherent catalog center is predicted outside the ±0.25 Å topocentric core in four epochs: January 2022 (−0.632657 Å), March 2022 (−0.382781 Å), December 2022 (−0.635715 Å) and March 2023 (−0.285920 Å). May 2022, May 2023 (+0.071201 Å) and July 2023 (+0.133503 Å) lie inside. These are metadata-derived coordinate predictions, not fitted peak positions. No window was recentered, and a fixed-core comparison can concern neighboring structure in an epoch whose catalog feature lies elsewhere.

C002's original core [3868.3525,3868.8525] Å was already visible in the completed C003 surrounding window, between its negative reference flank and core. Reciprocally, the complete original C003 core [3869.495,3870.0075] Å lies between the C002 core and positive flank, ending 0.095 Å before that flank. It is **not inside a C002 reference flank**. The broad windows overlap by 4.85125 Å with C003 and 2.3575 Å with C004. The C004 original core lies outside C002's ±3 Å window; the wider windows and observing products still overlap. Portions of both C002 flanks were seen previously. The fixed medians are structured reference levels, not established line-free continua. None of this is blind, untouched or independent validation.

The merged December 2022 barycentric profile and July 2023 profiles in both frames each retain one nonpositive source sample among 600 (0.166667%), belonging to the negative flank (1/150, 0.666667%). Other merged-window nonpositive fractions are zero. All 16 valid normalized profiles have false low-reference flags; the two raw-only order 2 flags are null. All 18 profiles have zero positive finite ERR support. Missing ERR and descriptive first-difference proxies do not establish calibrated uncertainties, significance, false-alarm rates, sensitivity or survey completeness.

## Preserved raw context and all-figure review

All four saved figures were inspected, including full titles, seven-epoch merged legends, native raw-only annotations and both complete raw/excess pairs. The merged figures retain every epoch and the one fixed catalog/discovery marker, signed/scaled views and shared vertical limits across frames. Order 2 stops visibly at its actual coverage edge; its normalized panels show only the merged curve with an explicit raw-only reason. Order 3 closely follows the merged shape after their separate fixed scaling. No plot, scale or frozen method was altered during review.

**The order 3 full-cutout scale is dominated by a bright compact patch toward the lower right, spatially separated from the nominal central feature context.** The smoother central band is faint on that full scale. This separate patch was already explicitly retained in the historical secondary review, which states, “Separate off-event pixel retained as context.” The primary/adopted shorthand about smooth trace-centered enhancement describes the central feature, not every structure in the cutout. The full-scale figure preserves both; the remote patch is not assigned to the catalog event or given a new origin classification. No new pixel statistic, registration, subtraction or spatial model was computed. Order 2's stored panel remains noisy and retains its historical local/baseline mapping limits. Neither central smoothness nor the remote bright patch alone resolves the event's physical origin.

The independent arithmetic audit passes 456 checks across 71,071 scalar values, without importing production functions. Source flux, ERR, indices and profile metrics agree exactly; the small interpolation/wavelength differences are separately recorded in the audit. This is computational verification, not human peer review or new observing evidence. All prior dispositions and outputs remain unchanged.

The next original-queue choice was frozen before these results: **C008 / V2E2-0047**, singleton row 17 at 5182.005 Å, with its one March 2023 discovery reference. NEXT_GROUP_METADATA.json and NEXT_STEP.md preserve the same-observation and original-analysis dependencies despite the distinct wavelength window. No C008 analysis was executed here.
