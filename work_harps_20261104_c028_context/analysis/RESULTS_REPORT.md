# C028 / HD126093 at 3864.5550000000003 air Angstrom

**Complete: six existing observations, one own April 27 discovery reference, sixteen profiles and thirty-two comparisons. V2E2-0260 remains U.**

All five other epochs have higher raw correlation and lower normalized RMS in the barycentric frame, in both the original core and surrounding spectrum. The central broad crest and broader structured pattern recur with amplitude and noise differences. This descriptive agreement does not identify a physical line, assign origin, qualify a laser candidate or calibrate significance, sensitivity or a survey null.

## Fixed scope and every nonself comparison

Preserve the exact original catalog center 3864.5550000000003 Å, core [3864.3050000000003,3864.8050000000003] Å and context [3861.5550000000003,3867.5550000000003] Å. The 0.01 Å grid has 51 core and 550 surrounding points. Own discovery ADP.2025-04-28T01:01:15.579 was observed on 2025-04-27 at BERV 5.77068898867443 km/s and fixes topocentric anchor 3864.480612819388 Å. No center, width, lag, stellar RV, drift, continuum, background or mask was fitted.

Each cell is **barycentric / topocentric**. Five rows represent five other observations against one fixed reference within the six-observation cohort. Four identical-product self rows remain labelled and add no recurrence evidence.

| Other observation | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2025-05-29 | 0.995170 / -0.468841 | 0.993113 / -0.017367 | 0.096928 / 1.217143 | 0.080465 / 0.784904 |
| 2025-05-30 | 0.995580 / -0.444378 | 0.993130 / -0.013751 | 0.139421 / 1.236222 | 0.093966 / 0.782247 |
| 2025-06-25 | 0.951639 / 0.392563 | 0.947710 / -0.059392 | 0.211042 / 0.765753 | 0.218483 / 0.904533 |
| 2025-06-27 | 0.995192 / 0.392586 | 0.987572 / -0.046170 | 0.086308 / 0.803152 | 0.087663 / 0.876075 |
| 2025-07-16 | 0.991134 / 0.382232 | 0.985286 / -0.011451 | 0.090348 / 0.834926 | 0.094628 / 0.849564 |

[All six original-core profiles](caption_correction/figures/MERGED_CORE_CONTEXT.png) · [Complete surrounding spectrum](caption_correction/figures/MERGED_BROAD_CONTEXT.png)

The discovery has higher signed raw amplitude than the other observations. The central crest aligns barycentrically after the fixed scalar normalization, while neighboring peaks and troughs remain inside the unchanged windows. June 25 has much lower raw flux and visibly noisier scaled structure; it also has the lowest barycentric shape agreement of these five nonself comparisons. It remains included. These observations are descriptive, without a fitted amplitude or linewidth, a line identification or a calibrated recurrence test.

## Finite support, signed samples and references

All sixteen profiles have 601 finite raw and normalized grid points, valid positive pooled flank references and false low-reference flags. None is partial, raw-only or blocked. All thirty-two Pearson and thirty-two normalized RMS values are evaluable. Every profile has zero positive finite ERR samples. Full coverage and false low-reference flags do not establish formal SNR or general measurement quality.

Four frame-profile rows from two reused observations contain nonpositive original source samples. Every original sign remains, without clipping or a sign-flip normalization. Fractions below are the saved fractions of finite original samples in each fixed region; frame rows share their observing products.

| Observation | Frame | Nonpositive window fraction | Negative flank fraction | Positive flank fraction |
|---|---|---:|---:|---:|
| 2025-06-25 | barycentric | 0.010000 | 0.000000 | 0.006667 |
| 2025-06-25 | topocentric | 0.013333 | 0.013333 | 0.006667 |
| 2025-07-16 | barycentric | 0.003333 | 0.000000 | 0.000000 |
| 2025-07-16 | topocentric | 0.003333 | 0.000000 | 0.000000 |

June 25 retains reference levels 64.815281 / 57.656324 ADU and first-difference noise proxies 16.438986 / 16.818882 ADU (B/T). Both fixed low-reference flags are false despite the negative samples and noisier appearance. The proxy and flag are descriptive, without calibrated significance or a formal noise model.

Discovery reference details, separately from interpolated 601-point support:

| Product / frame | Pooled reference | Finite original flanks L/R | Finite original window samples |
|---|---:|---:|---:|
| merged ADU / barycentric | 614.03692627 | 150 / 150 | 600 |
| merged ADU / topocentric | 614.03692627 | 150 / 150 | 600 |
| native order 2 (unit unspecified) / barycentric | 230.380996704 | 158 / 165 | 647 |
| native order 2 (unit unspecified) / topocentric | 230.380996704 | 158 / 165 | 647 |
| native order 3 (unit unspecified) / barycentric | 386.496246338 | 131 / 134 | 529 |
| native order 3 (unit unspecified) / topocentric | 386.496246338 | 131 / 134 | 529 |

The flanks contain structured source samples, including part of the next C029 feature. They are not established line-free continua. Native BUNIT is absent and merged ADU is uncalibrated; the separate native/merged divisors do not define physical flux ratios.

## Own native orders and preserved raw morphology

A fresh scan of all 72 native headers selects orders 2 and 3. Both frames geometrically cover the core, ±3 context and both flanks in each order. Actual finite support was subsequently measured, as above. The native products compare only with their own discovery merged extraction:

| Order / frame | Core raw r | Surrounding raw r | Core normalized RMS | Surrounding normalized RMS |
|---|---:|---:|---:|---:|
| 2 / barycentric | 0.990908 | 0.876369 | 0.134597 | 0.309043 |
| 2 / topocentric | 0.990908 | 0.876362 | 0.134594 | 0.309043 |
| 3 / barycentric | 0.998422 | 0.928403 | 0.169339 | 0.230610 |
| 3 / topocentric | 0.998422 | 0.928405 | 0.169338 | 0.230600 |

[Both native orders against their own merged extraction](results/figures/NATIVE_ORDERS_1.png)

The central extracted crests agree in shape; surrounding agreement is weaker and normalized amplitudes differ. Both orders share one exposure and extraction lineage, so these are dependent comparisons. Original global support, local/baseline failures and later five-window support remain distinct for each order. Geometric or later mapping support does not erase the original failures or determine origin.

[Both complete original raw/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain every saved pixel and separate full scales. Both show a diffuse central multi-row enhancement; order 2 is weaker and noisier. The historical broad, trace-centered, photon-compatible description remains provisional U/U/U. Photon-compatible morphology is not proof of an astrophysical origin or a laser. No new raw crop, contrast variant, registration, background subtraction or detector statistic was introduced. C029/0261 compact off-trace contamination is a separate historical record and is not transferred to 0260.

## Frame geometry and next-window dependence

| Observation | Predicted coherent-center offset from fixed topocentric anchor (Å) | Inside fixed ±0.25 core |
|---|---:|---|
| 2025-04-27 | +0.000000000 | yes |
| 2025-05-29 | +0.181620090 | yes |
| 2025-05-30 | +0.187296716 | yes |
| 2025-06-25 | +0.310199767 | no |
| 2025-06-27 | +0.317418278 | no |
| 2025-07-16 | +0.377333102 | no |

3 of six metadata-predicted coherent centers fall inside the fixed topocentric core; 3 fall outside. These are predictions under a barycentric-coherence assumption, not fitted peaks or proof of full finite-feature coverage. A fixed core may sample neighboring structure. The cohort BERV span is 29.26984563734743 km/s; neither geometry nor frame agreement is a calibrated origin test.

Next C029 at 3866.125 Å reuses the same six observations. The nominal ±3 Å windows overlap by 4.430000000000291 Å. Its catalog center lies in the current positive reference flank; only part of its ±0.25 core lies in that flank. The current core also intersects only part of the next negative flank. The next route was selected and this overlap recorded before current values. Shared windows, flanks, pixels and products are dependent. No source-pixel independence, blind validation, new observation or extra observing time is claimed. The preceding C020 analysis used a different star and different observing products.

## Arithmetic and delivery corrections

The public fixed method and exact 23-file readback at commit `b574a386b0dd50aff095bcbf98bb1daf35124325` preceded current observed values. Source-only restoration and header checking passed 1,563 checks. The 97 compact synthetic checks and 1,449 separate scalar checks over 73,014 synthetic values passed before execution.

The separate observed reconstruction passes **439 checks / 63,658 scalar comparisons** across all eight bounded source inputs, sixteen profiles, thirty-two comparisons and two byte-exact original raw containers. Original flux, ERR and source indices agree exactly. Fixed numerical tolerances pass; wavelength/interpolation arithmetic is not claimed bitwise identical. Maximum absolute differences:

| Quantity | Maximum absolute difference |
|---|---:|
| comparison | 1.0844103393e-13 |
| input_barycentric_wavelength | 4.54747350886e-13 |
| input_metadata | 0 |
| input_signed_source_flux | 0 |
| input_source_error | 0 |
| input_source_indices | 0 |
| input_source_wavelength | 4.54747350886e-13 |
| profile_metric | 0 |
| profile_normalized_flux | 1.2288836615e-11 |
| profile_offset | 0 |
| profile_requested_bary_wave | 0 |
| profile_signed_raw_flux | 2.83108647636e-09 |

An initial release JSON-format error stopped validation before any observed array access or result-directory creation. A newline-only release-metadata repair is recorded in [the repair receipt](RELEASE_FORMAT_REPAIR.json); the public method and plan were unchanged. The successful observed calculation ran once.

The original frozen renderer inherited **R021** in the two merged-image titles. All plan/event identities and numerical values correctly use **C028/R029**. Separate [caption-corrected copies](caption_correction/CORRECTION.json) change only that label to R029. The changed-pixel boxes are [869,34,881,50] in both 1820×1120 images; every pixel below the title band is identical. The original four PNGs, original renderer and numerical outputs remain unchanged. There are four scientific display views and six preserved PNG files including the two corrected copies. All six were visually inspected and fully decoded.

All 47 fixed source bindings and all original numerical hashes remain unchanged. Separate scalar formulas and fresh processes were run by the same assistant, without an independent human or separate-agent review claim.

[Plan](PLAN.json) · [Release](ROOT_RELEASE.json) · [All profile metrics](results/PROFILE_METRICS.csv) · [All comparisons](results/COMPARISONS.csv) · [Output hashes](results/OUTPUT_HASHES.json) · [Scalar audit](../independent_audit/NUMERICAL_AUDIT.json)

**Next:** C029/R030 on HD126093, original queue row 63 onward, records V2E2-0261/0266/0272 at exact 3866.125 Å. Preserve all three discovery references and six observing products, every per-record/order mapping stage and 0261 compact off-trace deposit/possible blend separately from its centered broad component. Restore its own products/raw containers, freshly scan all 72 headers per discovery and freeze a distinct fixed comparison before new arithmetic. See [the handoff](../NEXT_ACTION.json). C028 and all earlier exact diagnostics remain closed with physical U unchanged. Rubin remains limited feasibility with minimum 50 unmet.
