# Post-hoc O I three-line follow-up

This addition strengthens an atmospheric component interpretation without changing any detector, hit, disposition, or candidate-origin decision. It analyzes the already selected 25 provisional O I events plus V2-0165 and V2-0205, spanning 18 native exposures, and every available main-sample epoch of HD119130 (7) and HD120411 (11). It adds no observing exposure or independent survey trial.

## Main findings

- Of the 18 native exposures, 15 have STAR,WAVE with the FP selector, two have STAR,DARK with no B extraction, and one has STAR,SKY with an actual simultaneous B extraction. An e2ds_B filename alone is therefore not evidence of a sky control.
- That actual sky control is HD119130, 2023-05-14 (ADP.2023-05-15T01:01:10.510), containing V2-0163, V2-0164 and V2-0165. Its B spectrum has narrow excesses at all three fixed O I positions, fitted within 0.0025 Å of their reference centers. This independently supports an atmospheric contribution to the A spectrum. The existing raw-pixel evidence for V2-0165 remains: an atmospheric component and a compact detector charge event can coexist.
- A/B model-area scale factors from 5577 and 6300 are 0.8401 and 0.9025. Applied separately to B6363, they predict 15.07–16.19 ADU Å versus the observed A6363 area of 56.79 ADU Å. The residual is 40.60–41.72 ADU Å. These are a descriptive comparison, not an uncertainty interval, measured fiber throughput, or definitive deblending. No charge pixels were removed. A6300/A6363 is 0.946; B6300/B6363 is approximately 3.318.
- For V2-0205 (HD120411, 2022-05-24), A5577, A6300 and A6363 are all positive narrow structures whose best grid offsets are +0.0025, +0.0025 and −0.0025 Å. The native 6300/6363 model-area ratio is 2.595; the merged-spectrum value is 2.558. This strengthens the O I hypothesis, but fiber B contains FP calibration light, and no independent sky control or flux calibration establishes its origin. The existing unresolved disposition is preserved.
- All 25 originally provisional O I events have native best-fit offsets between −0.005 and +0.015 Å. Only two of those 25 have an independent sky control (V2-0163/0164). This is consistency within a preselected line population, not a new detection rate or proof that every event is atmospheric.
- All 18 target epochs, including epochs without a saved hit, are plotted and tabulated. The weak 6363 structure in some epochs is poorly constrained by this local model; boundary fits and stellar absorption/blends are retained rather than discarded. Positive signed amplitudes alone do not establish a detection.

## Reproducible procedure and safeguards

PLAN.json was written before the new flux measurements. The fixed air references are 5577.339, 6300.304 and 6363.776 Å. Native e2ds wavelength polynomials are evaluated directly; merged barycentric-air wavelengths are divided by (1+BERV/c), an approximate inverse correction. Sideband straight-line baselines use offsets 0.15–0.35 Å on each side; signed Gaussian amplitudes use a fixed FWHM of lambda/115000 and a ±0.08 Å core. All 33 center trials from −0.04 to +0.04 Å are saved. This is a fixed descriptive line measurement, not a matched-filter detection analysis.

SKY_CONTROL_PLAN.json was written after discovering the actual sky configuration and before the additional empirical A/B scaling. It keeps both scale factors and prohibits interpreting their spread as a confidence interval. Both plans identify their post-hoc status.

analyze_oi.py verifies SHA-256 of each selected native TAR/raw pair and each merged input. Raw header DATE-OBS is checked against science metadata. 102 native measurements and 54 merged measurements retain arrays, all center trials, and signed amplitudes. verify_oi.py independently recomputes all 156 baseline/amplitude/area values with closed-form regression and checks that the three original catalog/disposition hashes are unchanged. The first attempted run failed because a B header omitted BERV; its code and log are preserved in attempts/. The corrected version takes the informational BERV from the same-exposure science metadata; no BERV correction is applied to the native wavelength polynomial. No scientific measurement setting changed.

Run from the project root with the project Python dependencies available:

```sh
python v2/oi_followup/analyze_oi.py
python v2/oi_followup/plot_oi.py
python v2/oi_followup/sky_control.py
python v2/oi_followup/verify_oi.py
```

## Physical interpretation and limitations

NIST ASD gives the adopted air wavelengths. Its transition probabilities imply, by summing the listed M1 and E2 channels from the common upper level, an optically thin 6300/6363 photon branching ratio about 3.10 and energy-flux ratio about 3.13. This is our inference from the atomic probabilities, not a measured calibration of these data. The green line has a different upper level and does not have a fixed branching ratio with the red doublet.

The spectra use ADU with wavelength-dependent instrument response, blaze, order extraction, and stellar continuum. Consequently their raw-count area ratios cannot be used as precision physical branching ratios. The B sky extraction has near-zero continuum, so it is not continuum-normalized. Stellar blends, imperfect local continua, different fiber responses, profile mismatch, possible charge contamination, and unverified fine drift corrections limit centroids and areas. Every merged ERR array is unavailable/NaN; local sideband MAD values are descriptive scatter, not calibrated uncertainties or detection significance. The resolution and profile were held fixed rather than fitted or independently calibrated. The entire selection and physical-line follow-up are post hoc.

## Files

- ANCILLARY_FIBER_INVENTORY.json: TAR membership, raw/native mode headers, independent-sky availability and source hashes.
- NATIVE_MEASUREMENTS.*, ALL_EPOCH_MEASUREMENTS.*: full signed measurements; JSON includes every grid trial.
- OI25_FOLLOWUP.*: one row per provisional O I event with the existing disposition preserved.
- DESCRIPTIVE_DOUBLET_RATIOS.* and SKY_CONTROL_RESULT.json: explicit uncalibrated comparisons.
- figures/SIMULTANEOUS_SKY_CONTROL.png and HIGHLIGHT_THREE_LINES.png: key comparison; six native pages and two all-epoch pages retain the complete measured set.
- arrays/: 156 small numerical cutouts; no source FITS is duplicated here.
- VERIFICATION.json, SOURCES.json, EVIDENCE_MANIFEST.json and OI_FOLLOWUP_EVIDENCE.zip: audit trail and compact evidence bundle.

## Sources

1. NIST Atomic Spectra Database, O I air wavelengths and transition probabilities: https://physics.nist.gov/PhysRefData/ASD/lines_form.html (exact query preserved in SOURCES.json).
2. ESO HARPS User Manual v2.4, fiber modes and cross-fiber calibration context: https://www.eso.org/sci/facilities/lasilla/instruments/harps/doc/manual/HARPS-UserManual2.4.pdf
3. ESO HARPS Phase 3 release description, observation-type mapping: https://www.eso.org/sci/observing/phase3/data_releases/harps.pdf
4. ESO product-format guidance, e2ds/s1d and B-product interpretation: https://support.eso.org/en-US/kb/articles/harps-how-to-get-the-pipeline-generated-files-ccf-s1d-e2ds-bis-int-guide
