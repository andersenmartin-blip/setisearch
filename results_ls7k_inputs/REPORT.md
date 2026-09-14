# LS7K instrument-response input inventory

Completed 14 September 2026. This is a checked input packet for the same closed sectors.

**8,020 timing rows and 50/50 PRF files restored; raw-input audit PASS.**
Expected finite 117-by-117 primary/uncertainty pairs: **50/50**.
No response was fitted or detector evaluated.

| Sector | Camera/CCD | Timing rows | TIMECORR range (seconds) | Nominal detector x/y |
|---|---|---:|---:|---|
| 29 | 4/3 | 4010 | -102.650982 to -74.428544 | 763.412344, 259.908569 |
| 32 | 4/4 | 4010 | -91.393922 to -53.217872 | 1703.458344, 560.313001 |

Timing extracts include original TIME, TIMECORR, their spacecraft-time difference,
cadence IDs and quality values. Full FITS headers preserve the time and WCS conventions.
The raw light-curve bytes match LS7J, including every reused motion value.
This does not identify a timing defect in LS7J, which already used the same cadence IDs.

Engineering index status: **listed**; **4** matching sector-29/32 links recorded.
These are an availability inventory. No engineering samples or time-reference claims
are included in this stage.

PRFs are preserved as original FITS files in prf/. SHA-256 identifies every acquired
file. The complete inventory includes failed retrievals, image dimensions, finite and
negative counts, normalization diagnostics and headers. No array was shifted, clipped,
normalized or chosen using a signal/control outcome.

The [provenance assessment](../LS7K_PROVENANCE.md) supplies primary references and the
remaining response contract: coordinate conventions, temporal averaging, calibration
uncertainty and upstream target dependence. The configured grid covers both CCDs without
claiming a verified calibration-to-science coordinate conversion.

Next prepare a separately specified coordinate/PRF forward-model benchmark using these
closed inputs. Resolve the 44-column convention and subpixel layout from actual headers
before applying a model; expose any unverified motion-estimator assumptions.
LS7J remains closed. There is no new candidate, observing coverage or unused-data study.

## Reproducibility

Source freeze: 4084f29a0ad1be192a0126a378f128f22d0fb572.
Execution: [GitHub run 34828406647](https://github.com/andersenmartin-blip/setisearch/actions/runs/34828406647).

[Protocol](../LS7K_INPUT_PROTOCOL.md), [complete inventory](inventory.json),
[audit](AUDIT.json), [source checksums](source_freeze.json), [result checksums](SHA256SUMS).
The audit independently reopens both old light curves, compares 16,040 motion values,
recomputes the timing subtraction, checks the physical WCS by direct arithmetic,
and verifies all acquired PRFs and the historical manifests.
