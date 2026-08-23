# Milestone 25 report: HD 164922 held-out detector-v0.5 search

Status: **NO SURVIVING CANDIDATE; ALL 83 OVER-THRESHOLD CLUSTERS ARE VETOED AS RFI OR INSTRUMENTAL**.

Milestone 25 applied frozen detector v0.5.0 to the sole complete compatible
GBT L-band HD 164922 cadence `--84744`. HD 164922 b supplies only the motion
template; the search does not assume that an emitter is located on the planet.

GitHub Actions run `32656124838` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9497693760`, named `milestone-25-held-out-results`, has verified digest
`sha256:d40bb57d4fe35eca7cc22302636834122264febc2f7c92985254c648b617674a`.
All nine result files match `RESULTS_MANIFEST_M25.sha256`; the data manifest
contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Global result

Across approximately **592,487,280** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 78.602419** at 1406.207696457 MHz;
- scrambled-null median: **S/N 6.388315**;
- scrambled-null 99th percentile and operational threshold:
  **S/N 8.008045**;
- empirical global p-value: **1/257 = 0.00389105**; and
- final frozen disposition: **matched OFF-source RFI; no survivor**.

The maximum is stronger at the exact matched hypothesis in OFF data, S/N
116.324255. The OFF global maximum reaches S/N 119.232828. The low empirical
rank therefore reflects structured local interference, not evidence of an
astrophysical or artificial source.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p | Frozen maximum disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 5.662 | 1400.731912991 | 9 | 5.607 | 0.618677 | below threshold |
| 1406.0-1407.0 | 78.602 | 1406.207696457 | 9 | 119.233 | 0.003891 | matched OFF source |
| 1412.0-1413.0 | 5.448 | 1412.482102302 | 9 | 7.215 | 0.945525 | below threshold |
| 1418.0-1419.0 | 5.814 | 1418.132532932 | 3 | 5.814 | 0.342412 | below threshold |
| 1424.5-1425.5 | 12.471 | 1424.892605307 | 9 | 14.864 | 0.003891 | local OFF source |

Window p-values measure departure from the circular-shift null and do not
override the fixed physical OFF and receiver-frame evidence.

## Complete disposition accounting

The prospectively fixed 1200-cluster cap retained every one of the 216
clusters. **83** exceeded the global threshold:

| Physical disposition | 1406 MHz | 1425 MHz | Total |
|---|---:|---:|---:|
| exact matched OFF-source recurrence | 21 | 1 | 22 |
| local OFF-source recurrence | 21 | 20 | 41 |
| receiver-frame template alias | 15 | 0 | 15 |
| single adjacent-OFF track | 0 | 5 | 5 |
| **survivors** | **0** | **0** | **0** |

The remaining 133 clusters were below threshold. Arithmetic-frequency-family
and widest-template flags are treated only as triage evidence; each
above-threshold rejection is based on a frozen physical OFF-source or
receiver-frame criterion.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 3/32 (9.4%) | 3/32 (9.4%) |
| 12 | 31/32 (96.9%) | 27/32 (84.4%) |
| 16 | 32/32 (100%) | 29/32 (90.6%) |
| 20 | 32/32 (100%) | 29/32 (90.6%) |
| 24 | 32/32 (100%) | 29/32 (90.6%) |
| 32 | 32/32 (100%) | 30/32 (93.8%) |
| 40 | 32/32 (100%) | 30/32 (93.8%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **9.86** and **11.69**. The corresponding one-channel
estimates are **10.17** and **15.60**. These are grid interpolations, not
confidence bounds.

## Independent-cadence boundary

The frozen screen contains no second qualifying HD 164922 L-band cadence;
`--82207` is S-band. No primary case survived the automatic physical vetoes,
so Milestone 25 closes as a primary-cadence null result. This archive selection
could not have established independent recurrence even if a case survived.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three ON scans belong to one approximately 35-minute cadence on
  2016-03-10, not independent observing nights.
- Two controls use the archive source label `HIP88348_OFF`; the last uses
  HIP87938. They are the frozen OFF observations supplied by the cadence.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on HD 164922 b.
- The minimum empirical p-value measures departure from the circular-shift
  null. Stronger matched and local OFF structure identifies non-unique local
  features.
- The null result constrains only the frozen frequency windows, signal model,
  cadence, and measured sensitivity.

## Reproducibility

The public preregistration commit is
`8e92aa1c20f543ea62b2d532bdbdeca2bfb39e94`; the execution commit is
`76bf13d87b9227c03028be005c9a32a8e7d46af3`. The frozen configuration SHA-256
is `3ab7ea6e4a73f4ecbb024690148c2419de42df69fba461442972d0733af09868`.
The complete search record SHA-256 is
`430c1894f289c9fc4015945633b65ee89b46f45a17824498c2b750835ba5671e`.
`DATA_MANIFEST_M25.sha256` identifies all 30 reproducible extracts and
`RESULTS_MANIFEST_M25.sha256` identifies all nine published outputs. Extracted
telescope slices are not committed.
