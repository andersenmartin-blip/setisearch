# Conditional comparison of the ten fixed HARPS events

**The comparison is prepared; no new spectral arrays have been read.** It covers the existing six HD122640 and four HD135204 U records in the declared catalog order. The exact twenty discovery-frame profiles have been restored from the original archive and verified byte for byte (178,172 bytes). They come from seven discovery exposures. The original 100-spectrum epoch analysis is not rerun.

## Exact existing references

| Event | Target | Discovery DP | Barycentric air center, Å | Discovery BERV, km/s |
|---|---|---|---:|---:|
|V2E2-0229|HD122640|ADP.2023-02-21T01:01:25.308|3868.9275000|27.2411836964|
|V2E2-0231|HD122640|ADP.2023-02-21T01:01:25.308|3881.2050000|27.2411836964|
|V2E2-0234|HD122640|ADP.2023-02-23T01:01:36.791|3868.9250000|26.7848884193|
|V2E2-0235|HD122640|ADP.2023-02-23T01:01:36.791|5548.0900000|26.7848884193|
|V2E2-0236|HD122640|ADP.2023-02-25T01:01:19.535|3866.9600000|26.3486734120|
|V2E2-0237|HD122640|ADP.2023-02-25T01:01:19.535|3868.9250000|26.3486734120|
|V2E2-0303|HD135204|ADP.2023-02-21T01:01:25.320|3871.0825000|28.1529168427|
|V2E2-0305|HD135204|ADP.2023-02-24T01:01:17.507|3871.0800000|27.7944193828|
|V2E2-0308|HD135204|ADP.2023-02-25T01:01:19.543|3871.0850000|27.6015151567|
|V2E2-0309|HD135204|ADP.2023-02-26T01:01:15.129|3871.0850000|27.5778777500|

`EVENTS.json` retains full precision, original input hashes and already saved header metadata. `DISCOVERY_PROFILES.csv` gives both exact NPZ archive members and SHA256 values for every event. `EXISTING_REFERENCE_RECEIPT.json` binds these to the original queue, catalog, metric code, profile metadata and all eighteen ordered archive parts. The reference spectra use HARPS_3.8, barycentric air wavelengths in angstrom, ADU flux, and no finite original ERR samples.

## Method reused without changes

The guarded runner imports the hash-verified original `epoch_followup/measure_epochs.py` and calls only `profile`, `corr` and `stats`. It never calls the original `main`. The fixed grid remains −1 to +1 Å in 0.01 Å steps; interpolation never extrapolates and masks input brackets wider than 1.51 times the median input step. The positive-median normalization uses native flux within ±2 Å of the requested **barycentric** center. A constant+slope background uses fixed |offset|≥0.60 Å sidebands and at least twenty finite points.

Correlation compares the separately archived discovery residual for the same event/frame with the new residual, at zero shift in |offset|≤0.25 Å and at least twenty shared finite samples. No lag or line center is optimized. Signed Gaussian templates are fitted to normalized flux together with their own constant+slope terms, at fixed FWHM=center/115000 and three times that width. Amplitude/RMS and first-difference noise proxies are descriptive, not SNR or measured linewidths.

Barycentric comparison uses the accepted discovery center unchanged. Topocentric comparison uses center_top=center_bary/(1+BERV_discovery/c) and queries each new barycentric spectrum at (center_top+offset)×(1+BERV_new/c), with c=299792.458 km/s. The topocentric offset grid therefore must use its own archived discovery profile. This classical conversion is not a stellar radial-velocity, instrumental-drift or full relativistic correction.

## Input selection and compatibility gates

The separately frozen header selection chooses minimum then maximum recorded BERV for HD122640 and then HD135204, with lexicographically smallest DP-ID ties and duplicate extrema removed. At most two new epochs per target are allowed. The comparison independently reconstructs this selection from all passing header results; no new flux enters it. Old raw progenitors and duplicate selected progenitors are rejected. If no useful or compatible header sample exists, this remains prepared work.

Before any new `.data` access, all acquired payload headers must be inspected. Compatible inputs require exact identity/provenance and recorded primary-header agreement, NCOMBINE=1, SPECSYS=BARYCENT, SPEC_RES=115000 and explicit ESO INS HEFS ST=False. Actual INS MODE is retained: a label such as HARPS+NIRPS is not equated with HAM or EGGS by its name. The single-row spectral table must provide unambiguous WAVE/FLUX/ERR columns, air-wavelength angstrom metadata and ADU flux. Duplicate or blank column names are rejected. No silent representation conversion is performed.

Finite, strictly increasing wavelength and matching one-dimensional arrays are checked after the header pass. Missing acquisitions, incompatible headers and invalid arrays retain their selected event/frame slots. They are never replaced according to flux appearance. With two accepted epochs for each target, the expected output is 20 event/epoch pairs and 40 frame profiles; fewer selected epochs reduce that declared count. All ten original events remain in the event summary.

Pipeline versions and instrument-mode metadata are recorded, including differences from HARPS_3.8. Matching units and nominal resolution do not calibrate changes in extraction, blaze/background, line-spread function, hardware epoch or wavelength zero point. These comparisons cannot establish origin from a frame preference alone.

## Execution and restoration

`PLAN.json` specifies the release contract. The runner requires a root release tied to the public freeze/readback, prospective plan/code, exact header-based selection, header evidence, acquired-product manifest, receipts and payload hashes. Its ordered input list must equal the canonical acquisition manifest. No network operation exists in the comparison runner.

```bash
python3 compare_verified_epochs.py --release COMPARISON_RELEASE.json
```

The default absent release blocks execution. A pre-existing results directory also blocks an accidental rerun. The runner rechecks the release, original method/reference metadata, all twenty reference files, header/receipt evidence and acquired payload hashes at completion. The final status distinguishes completed, partial and entirely blocked comparisons. No U classification or binary repeat/origin label changes.

The local `inputs/` cache is ignored by Git and is reproducible. In a separate copy, `prepare_existing_references.py` verifies all eighteen original archive parts and their reconstructed ZIP hash, then extracts only the twenty exact members; it does not interpret their arrays or download anything. The preparation receipt refuses overwrite, so retain the existing receipt or reproduce in a fresh directory.

Original survey denominators remain unchanged. Additional archival context is neither a new blind search nor newly commissioned telescope time, and supplies no calibrated sensitivity, false-alarm rate or extraterrestrial evidence.
