# Milestone 23 primary result: HD 33564 held-out search

Status: **PRIMARY SEARCH COMPLETE; COMPLETE OVER-THRESHOLD DISPOSITION AUDIT REQUIRED**.

GitHub Actions run `32649374111` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9495958561`, named `milestone-23-held-out-results`, has verified digest
`sha256:67e3ea6cbf9235875bb98a1326bbac542db4112ef1c1f81750d9bc8d62b46845`.
All nine primary result files match `RESULTS_MANIFEST_M23.sha256`; the data
manifest contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Global result

Across approximately **592,487,280** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 184.273162** at 1400.135544237 MHz;
- scrambled-null median: **S/N 6.575475**;
- scrambled-null 99th percentile and operational threshold:
  **S/N 7.945475**; and
- empirical global p-value: **1/257 = 0.00389105**.

The global maximum is reproduced at the exact matched hypothesis in OFF data
at S/N 164.785674 and by the local OFF search at S/N 273.743719. It receives
the frozen `rfi_veto_off_source` disposition and is not a survivor.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p |
|---|---:|---:|---:|---:|---:|
| 1400.0-1401.0 | 184.273 | 1400.135544237 | 5 | 339.149 | 0.003891 |
| 1406.0-1407.0 | 6.773 | 1406.642977425 | 9 | 6.473 | 0.007782 |
| 1412.0-1413.0 | 5.882 | 1412.503178599 | 5 | 13.115 | 0.307393 |
| 1418.0-1419.0 | 9.051 | 1418.949424459 | 3 | 72.376 | 0.003891 |
| 1424.5-1425.5 | 7.839 | 1425.216944368 | 9 | 7.628 | 0.003891 |

The four reported 1418 MHz clusters above the global operational threshold
all receive a frozen physical OFF veto: three local-OFF and one exact
matched-OFF. The maxima in the 1406, 1412, and 1425 MHz windows are below the
global threshold.

## Report-cap boundary

The 1400 MHz window formed 124 clusters above the fixed S/N 5.5 reporting
floor, but the preregistered output cap retained only the 50 strongest. All 50
are automatically vetoed (27 exact matched-OFF, 21 local-OFF, and 2
receiver-frame aliases), but the weakest reported case still has S/N
10.857115, above the global operational threshold of 7.945475.

Therefore the unreported 74 clusters cannot be assumed to be below threshold
or physically vetoed. The primary result does **not** yet support a complete
no-survivor statement. The report limit is an output-capacity issue, not a new
signal or a failure of the frozen statistical calibration.

## Required audit

A separately frozen audit must rerun the identical primary cadence and
detector with only `max_report_clusters` increased from 50 to 500. It must
reproduce the primary data hashes, global scores, null calibration, and first
50 reported clusters, then preserve all 124 clusters and apply the unchanged
v0.5 dispositions. No threshold, signal model, search window, orbital
template, OFF rule, or seed may change.

Cadence `--71747` remains spectrally untouched. It may be opened only if the
complete audit leaves a case above threshold without a frozen physical veto.
