# Blue comb: native fiber and spatial contamination follow-up

The evidence supports a provisional calibration-ghost contribution for V2-0001, V2-0103 and V2-0104. It goes beyond a wavelength-region match: both reference raw images contain an oblique train of bright spots crossing the science extraction trace near the saved candidate positions. Every original unresolved disposition is preserved; the physical parent order and exact reflected wavelength mapping have not been established.

## Measurements

We checked all 11 locally available native exposures for the two targets: five HD103991 and six HD114386 exposures. All have STAR,WAVE and the FP selector, with an actual fiber-B extraction. None supplies an independent sky control. There are 44 native A/B/order/group cutouts and 32 direct A/B spectral comparisons. Eleven other main-sample epochs have merged spectra but no native product in the existing local collection; the epoch study covers those separately. No new data were downloaded and no exposure credit is added.

| Event / group | Reference topocentric air wavelength | Reference raw trace | Off-trace ridge slope (columns/row) | Predicted ridge offset at withheld candidate row |
|---|---:|---|---:|---:|
| V2-0001 / E01 | 3852.190680 Å | A order 2 | −0.078 | −0.25 column |
| V2-0103 / E10 | 3822.679329 Å | A order 1 | −0.074 | +1.00 column |
| V2-0104 / E11 | 3822.831815 Å | A order 1, same exposure as E10 | same E10 fit | +2.001 columns |

The fitted slopes correspond to about 4.46° and 4.23° relative to the raw dispersion direction. These are descriptive measurements of the visible oblique pattern, not the exact angle relative to the slightly curved science traces.

For E01, the fit uses 458 off-trace pixels distributed across 72 lower and 87 upper rows. For E10 it uses 452 pixels across 77 lower and 108 upper rows. Every pixel within six columns of any predicted main A/B trace is excluded. Every row within 80 pixels of the candidate is also excluded from fitting. Thus the near-crossing is evaluated on a withheld spatial interval, although the decision to fit this family of oblique structures was made after visually inspecting the full image. E11 is a second position in the same image and is not an independent exposure or independent ridge fit.

The direct same-wavelength A/B high-pass correlations are small: across all 32 comparisons, r ranges from −0.192 to +0.133. The reference E01 A2/B2 comparison is −0.009; E10 A1/B1 is −0.027 and E11 is −0.021. There is no strong direct copy at the same physical wavelength in the neighboring B extraction. This does not test a ghost that redirects a spectrum from another detector position or spectral order. Do not optimize a free wavelength shift and call its best peak an identified parent.

The separate epoch analysis finds that E10/E11 align better in the observer frame over 11 merged epochs and about 615 days: median pairwise correlations 0.825/0.774 versus 0.116/0.468 barycentrically. E01 also favors the observer frame (0.851 versus 0.740) but over only about 10 days. These are imported contextual results, not repeated independent measurements. Exact source hashes and numbers are preserved in EPOCH_CONTEXT.json.

## Interpretation and counterexamples

A comb of distinct bright spots follows an oblique path through otherwise separate science and FP traces. Combined with the FP configuration, recurrence in the observer frame, and published HARPS ghost morphology in this broad region, this supports an instrumental reflected-calibration hypothesis for these three events. It does not establish which B order produced the reflection, how its wavelengths map into the A order, or how much of each extracted feature is contamination versus ordinary stellar flux. A dedicated B-only calibration/ghost model would be needed for that stronger claim.

V2-0125 and V2-0139 are explicit counterexamples to assigning origin by proximity to 3852 Å. Although their single-epoch observer-frame positions are close, the separate all-epoch analysis finds barycentric persistence for both. We therefore do not extend the ghost interpretation to them. The approximate spacing similarity between selected event wavelengths is not used as independent evidence or a veto.

## Fixed plans, amendments, and audit

PLAN.json predates the new blue flux measurements. It fixes ±2 Å native windows, all covering orders, a 31-native-pixel median high-pass, direct unshifted A/B comparisons over ±1.5 Å, and reference raw patches ±250 dispersion rows / ±80 columns. Detector-boundary clipping is recorded; E01's second overlapping A order is near an edge and has much lower flux, limiting its usefulness. Peak lists are descriptive local maxima and are not a new detection catalog.

RIDGE_PLAN.json was written after inspecting the initial raw patches but before numerical ridge fitting. Its first optimizer allowed different amounts of unmasked support; E01's highest mean score used just one pixel. That result is invalid for identifying a trajectory. The full first-attempt code, grids, figures and log remain in attempts/. RIDGE_PLAN_V2.json explicitly records the correction before recalculation: every candidate path must have at least 200 unmasked pixels and 25 distinct rows on each side of the withheld interval. The same requirement is applied to both targets. All 7,371 trial paths per target remain in RIDGE_RESULTS.json, including ineligible paths. Scores carry no calibrated significance or error interval.

The initial native measurement run also hit a NumPy-boolean JSON serialization error at final output; its script and log are preserved. The sole correction was casting the window-completeness flag to Python bool, then rerunning the same plan. No measurement setting changed.

verify_blue.py independently recomputes all 32 correlations by the centered-moment formula, verifies both final ridge masks, two-sided coverage, scores and grid maxima, and checks frozen hit/disposition SHA-256 values. Every source TAR/raw pair was hash-verified when read. No original catalog, detector, threshold or disposition was changed. Root-agent visual review is recorded separately and is not presented as human review.

```sh
python v2/blue_calibration_followup/analyze_blue.py
python v2/blue_calibration_followup/fit_oblique_ridge.py
python v2/blue_calibration_followup/verify_blue.py
```

## Key artifacts

- figures/E01_RAW_o2.png and E10_RAW_o1.png: original wider raw and high-pass patches, all predicted main traces.
- figures/E01_OBLIQUE_RIDGE.png and E10_OBLIQUE_RIDGE.png: supported off-trace fits and withheld crossings.
- figures/E01_NATIVE_AB.png, E10_NATIVE_AB.png, E11_NATIVE_AB.png: native direct A/B comparison, independently scaled vertical axes.
- FIBER_INVENTORY.json, NATIVE_MEASUREMENTS.json, NATIVE_AB_COMPARISONS.json: complete native measurements and provenance.
- RAW_PATCH_METADATA.json, arrays/: numerical raw/native cutouts and header-based trace coordinates.
- RIDGE_RESULTS.json, VERIFICATION.json, ROOT_VISUAL_REVIEW.json: geometry, audit and visual-review scope.
- EVIDENCE_MANIFEST.json and BLUE_CALIBRATION_EVIDENCE.zip: compact verified evidence bundle; originals remain in the existing product manifests.

## Primary references

Cretignier et al. (2021), YARARA, Section 2.6, Figure 6 and Appendix B: https://arxiv.org/pdf/2106.07301 ; DOI https://doi.org/10.1051/0004-6361/202140986 . They identify FP-related reference-fiber ghost combs around 3822 and 3851 Å and model oblique reflections separately from the main spectral orders. Their broad-region result motivates the mechanism here; it is not an exact identification of our individual wavelengths. Their use of B-only flat/ghost maps also indicates why a physical parent-order assignment needs more calibration information.

ESO HARPS User Manual v2.4, simultaneous calibration modes: https://www.eso.org/sci/facilities/lasilla/instruments/harps/doc/manual/HARPS-UserManual2.4.pdf . ESO Phase 3 release description: https://www.eso.org/sci/observing/phase3/data_releases/harps.pdf . Native header FP selectors are retained so the inference does not depend solely on the general documentation.
