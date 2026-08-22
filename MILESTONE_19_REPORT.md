# Milestone 19 report: 47 UMa held-out detector-v0.5 search

Status: **NO CANDIDATE; NO FOLLOW-UP TRIGGERED**.

Milestone 19 applied frozen detector v0.5.0 to the previously unused complete
GBT L-band 47 UMa cadence `--73992`. 47 UMa d supplies only the motion
template; the search does not assume that an emitter is located on the planet.

GitHub Actions run `32584958611` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9478986265`, named `milestone-19-held-out-results`, has verified digest
`sha256:e8f1c4a5663662a090e17a52c445ce8ed07bbf17fafff456ff6e8bc965f93f42`.
All nine primary result files match `RESULTS_MANIFEST_M19.sha256`, and the data
manifest contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Global result

Across approximately **601,293,840** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 7.414668** at 1425.240493566 MHz;
- scrambled-null median: **S/N 6.439086**;
- scrambled-null 99th percentile and operational threshold:
  **S/N 7.698725**;
- empirical global p-value: **9/257 = 0.0350195**; and
- final frozen disposition: **below threshold; no candidate**.

The maximum uses template 4 (projected scale 0.25, phase +0.1 cycles), the
nine-channel width, and all three ON epochs. Its per-epoch values are
`[4.2809, 4.3619, 4.3700]`. The calibrated complete-search threshold is higher
than the observed statistic, so the preregistered rules do not permit a
candidate label or a targeted follow-up.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p | Frozen disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 6.980 | 1400.056046911 | 9 | 6.304 | 0.007782 | below threshold |
| 1406.0-1407.0 | 5.730 | 1406.625857070 | 3 | 5.584 | 0.369650 | below threshold |
| 1412.0-1413.0 | 5.487 | 1412.574649230 | 9 | 6.059 | 0.832685 | below threshold |
| 1418.0-1419.0 | 5.791 | 1418.466592528 | 9 | 6.839 | 0.287938 | below threshold |
| 1424.5-1425.5 | 7.415 | 1425.240493566 | 9 | 9.395 | 0.031128 | below threshold |

The window-level p-values are diagnostics; the frozen decision is based on the
global threshold after searching every band, motion template, activity subset,
and spectral width.

## Candidate reduction

The frozen reporting procedure retained 446 hypothesis peaks, formed 326
frequency clusters before report limits, and reported 89 clusters. Every one
of the 89 has the final disposition `below_threshold`. There are no automated
survivors, no morphology-only review cases, and no independent-recurrence
trigger.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 9/32 (28.1%) | 9/32 (28.1%) |
| 12 | 28/32 (87.5%) | 22/32 (68.8%) |
| 16 | 32/32 (100%) | 27/32 (84.4%) |
| 20 | 32/32 (100%) | 31/32 (96.9%) |
| 24 | 32/32 (100%) | 31/32 (96.9%) |
| 32 | 32/32 (100%) | 32/32 (100%) |
| 40 | 32/32 (100%) | 32/32 (100%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **9.47** and **12.80**. The corresponding one-channel
estimates are **10.15** and **17.80**. These are grid interpolations, not
confidence bounds; a 32/32 level has a Wilson 95% lower bound of 89.3%.

## Follow-up decision

The frozen protocol allowed a separately preregistered within-cadence
morphology review only if a case survived the global threshold and automatic
vetoes. None did, so that trigger did not fire. The header screen also found no
second complete compatible 47 UMa cadence. Milestone 19 therefore closes at
the primary null result.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three ON scans belong to one approximately 29-minute ABACAD cadence on
  2016-07-09, not independent observing nights.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on 47 UMa d.
- The null result constrains only signals present in at least two ON epochs and
  represented by the frozen template, width, and activity banks.
- It applies only to the frozen windows and measured sensitivity.

## Reproducibility

The public preregistration and execution commit is
`674eafcc08a8e4bc72946fac505e951582afc4d4`; the frozen configuration SHA-256
is `48b82d339409bc62f05fdbab1f4f3427bb7d0c73d8d1a29064527a210aba9823`.
`DATA_MANIFEST_M19.sha256` identifies the 30 extracted slices;
`RESULTS_MANIFEST_M19.sha256` identifies all primary published outputs. The
extracted telescope slices are not committed.
