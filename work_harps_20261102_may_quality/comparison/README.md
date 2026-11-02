# Separate post-hoc May-quality comparison

This phase prepares one additional archived exposure, `ADP.2017-05-21T01:01:50.278` (raw progenitor `HARPS.2017-05-20T02:21:45.847`), for the six fixed HD122640 event records. The candidate was selected for the highest average metadata SNR among unused May exposures in the saved pool after the previous May 22 exposure proved low-continuum near 387 nm. This is explicitly post-hoc follow-up. Average metadata SNR does not guarantee local spectral quality.

The completed prior 24-profile comparison remains immutable. This phase has exactly **six event/epoch pairs and twelve frame slots**, including any blocked slots. The full ten-record queue remains in `EVENTS.json`; HD135204 records V2E2-0303, V2E2-0305, V2E2-0308 and V2E2-0309 receive zero new epoch slots. No labels, centers, windows, fitted shifts, thresholds or origin assignments are changed.

The [prospective plan](PLAN.json) and both scripts were prepared before new header or payload acquisition. [OFFLINE_PREFLIGHT.json](OFFLINE_PREFLIGHT.json) records successful source-equivalence, compilation, source/reference hash and missing-release checks, with no new arrays or network requests.

## Release and compatibility gates

The acquisition owner requires separate public header and payload releases. The comparison additionally requires `COMPARISON_RELEASE.json` with schema `HARPS_MAY_QUALITY_COMPARISON_RELEASE_V1`, a 40-character publication commit, verified public readback, and SHA256 links to this plan/script, the exact candidate, header results, selection and acquisition manifest. `inputs` must exactly equal the manifest list; the only allowed identity is the fixed HD122640 product above.

The recorded header must pass all acquisition criteria and have a finite numeric BERV with an absolute displacement of at least **10 × 299792.458 / 115000 = 26.06890939130435 km/s** from each of the six fixed discovery BERVs. The comparator independently repeats this gate. Product and raw identities are checked against the original exposure set and both completed prior follow-up products. There is no replacement if the fixed candidate fails.

Every complete payload's headers are inspected before accessing any new spectral array. The unchanged header checker requires the recorded primary metadata, HARPS identity, a single raw exposure, BARYCENT frame, nominal resolution 115000, explicit HEFS=False, one table row, uniquely named WAVE/FLUX/ERR columns, air-angstrom wavelengths and ADU flux. Pipeline differences are retained as context. Invalid headers produce explicit blocked frame slots. Arrays subsequently require matching one-dimensional shapes and finite strictly increasing wavelengths. No sorting or unit conversion is silently introduced.

Successful, failed and unattempted acquisition slots remain explicit. A failed header selection produces no passing selected candidate and the comparator refuses execution. A selected candidate with failed/unattempted acquisition or incompatible payload headers produces twelve blocked slots. All input, receipt, method and discovery-reference hashes are rechecked after execution. Existing output directories are never overwritten.

## Unchanged measurements and existing references

The script imports the SHA-verified original `work_harps_20261101/v2/extension02/epoch_followup/measure_epochs.py` and calls its unchanged `profile`, `corr` and `stats` functions. Its original `main` is not called. Sampling remains ±1 Å with a 0.01 Å grid; normalization uses the local ±2 Å median; linear backgrounds use fixed |offset| ≥ 0.60 Å sidebands. Residual correlations are zero-shift Pearson values within ±0.25 Å. Signed Gaussian templates have fixed widths of λ/115000 and three times that width. These are descriptive amplitudes and noise proxies, not calibrated significance or measured line widths.

The barycentric accepted centers and the inherited BERV-based topocentric transformation remain unchanged. Barycentric wavelength is not a stellar rest frame; no stellar-RV or drift correction is fitted.

Twenty existing discovery NPZ files were copied from the previous phase's verified cache and checked against their archived hashes. [REFERENCE_CACHE_RECEIPT.json](REFERENCE_CACHE_RECEIPT.json) records this transfer; [EXISTING_REFERENCE_RECEIPT.json](EXISTING_REFERENCE_RECEIPT.json) preserves the original archive and member provenance. `inputs/` is an ignored working cache. The published original profile archive and its hash manifest remain the restoration source if that cache is unavailable. Neither prior spectra nor the original 100-exposure analysis are rerun.

After all release artifacts exist, root may execute once:

```bash
python work_harps_20261102_may_quality/comparison/compare_verified_epoch.py \
  --release work_harps_20261102_may_quality/comparison/COMPARISON_RELEASE.json
```

The script contains no network acquisition. Results, all ten event summaries, payload header validation and exact output hashes are written beneath `results/`.

## Declared presentation

[PLOT_PLAN.json](PLOT_PLAN.json) fixes seven figures before the new header or flux is inspected: six individual event figures showing the full ±1 Å normalized profiles and both ±0.25 Å residual cores, plus an overview of all six records in both frames. The four curves are discovery, the closed May 22 and January 20 profiles, and this separate May 20 quality-phase profile. The old 24 profile arrays are copied into the display without recomputing any measurement. Their original hash manifest is bound by the new plan and checked before and after plotting.

All finite displayed values determine axis limits with fixed padding; corresponding axes share limits across frames. Blocked slots remain explicit in the plot index. No lag, center or display selection is used to improve agreement. Once the new comparison is complete:

```bash
python work_harps_20261102_may_quality/comparison/plot_comparison.py
```

All six records remain correlated, with shared wavelength neighborhoods and exposure inputs. A successful geometric BERV gate does not establish adequate local SNR, a repeat classification, physical origin, false-alarm calibration or survey sensitivity. The new phase will report all six pairs and all quality flags, including an unfavorable or blocked result, while preserving the four uncovered HD135204 records and all ten U labels.
