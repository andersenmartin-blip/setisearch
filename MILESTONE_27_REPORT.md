# Milestone 27 report: HD 127506 held-out detector-v0.5 search

Status: **NO SURVIVING CANDIDATE; ALL 18 OVER-THRESHOLD CLUSTERS ARE VETOED AS CONTROL-SOURCE RFI**.

Milestone 27 applied frozen detector v0.5.0 to the sole complete compatible
GBT L-band HD 127506 cadence `--83509`. HD 127506 b supplies only the motion
template; the search does not assume that an emitter is located on the planet.

GitHub Actions run `32723600398` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9519133182`, named `milestone-27-held-out-results`, has verified digest
`sha256:ae147654a5ee914cc99e6ef31dcb937ee26f9c003f39dd082c95ef8fbd1fda57`.
All nine result files match `RESULTS_MANIFEST_M27.sha256`; the data manifest
contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Global result

Across approximately **601,293,840** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 102,410.860692** at 1406.485088594 MHz;
- scrambled-null median: **S/N 6.600017**;
- scrambled-null 99th percentile and operational threshold:
  **S/N 8.748774**;
- empirical global p-value: **1/257 = 0.00389105**; and
- final frozen disposition: **local control-source RFI; no survivor**.

At the maximum, the frozen local-control search finds S/N 100,368.040250 only
2.794 Hz away. The control global maximum reaches the same S/N and the
receiver-frame signatures coincide near 1406.250000 MHz in the implicated
epochs. The low empirical rank therefore reflects exceptionally strong,
structured interference shared with control observations, not evidence of an
astrophysical or artificial source.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | control-global S/N | Empirical p | Frozen maximum disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 56,169.662 | 1400.624733895 | 1 | 54,980.596 | 0.003891 | local control source |
| 1406.0-1407.0 | 102,410.861 | 1406.485088594 | 1 | 100,368.040 | 0.003891 | local control source |
| 1412.0-1413.0 | 47,374.696 | 1412.345443293 | 1 | 11.438 | 0.003891 | local control source |
| 1418.0-1419.0 | 48,230.936 | 1418.205795199 | 1 | 8.622 | 0.003891 | local control source |
| 1424.5-1425.5 | 16.598 | 1425.232491642 | 9 | 15.111 | 0.003891 | local control source |

Window p-values measure departure from the circular-shift null and do not
override the fixed global threshold or physical control-source evidence.

## Complete disposition accounting

The prospectively fixed 1200-cluster cap retained every one of the 299
clusters. **18** exceeded the global threshold:

| Physical disposition | 1400 MHz | 1406 MHz | 1412 MHz | 1418 MHz | 1425 MHz | Total |
|---|---:|---:|---:|---:|---:|---:|
| exact matched control-source recurrence | 6 | 1 | 0 | 0 | 0 | 7 |
| local control-source recurrence | 3 | 3 | 2 | 1 | 2 | 11 |
| **survivors** | **0** | **0** | **0** | **0** | **0** | **0** |

The remaining 281 clusters were below threshold. Receiver-frame-alias,
arithmetic-frequency-family, and widest-template flags provide additional
triage evidence, but every above-threshold rejection already satisfies a
frozen physical control-source criterion.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 2/32 (6.2%) | 2/32 (6.2%) |
| 12 | 20/32 (62.5%) | 13/32 (40.6%) |
| 16 | 32/32 (100%) | 20/32 (62.5%) |
| 20 | 32/32 (100%) | 28/32 (87.5%) |
| 24 | 32/32 (100%) | 29/32 (90.6%) |
| 32 | 32/32 (100%) | 32/32 (100%) |
| 40 | 32/32 (100%) | 32/32 (100%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **11.11** and **14.93**. The one-channel 50% and 90%
estimates are approximately **13.71** and **23.20**. These are grid
interpolations, not confidence bounds.

## Independent-cadence boundary

The frozen screen contains no second qualifying HD 127506 L-band cadence;
`--69234` is S-band. No primary case survived the automatic physical vetoes,
so Milestone 27 closes as a primary-cadence null result. This archive selection
could not have established independent recurrence even if a case survived.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three ON scans belong to one approximately 32-minute cadence on
  2017-06-23, not independent observing nights.
- The three alternating controls are archival sources HIP70142, HIP70297, and
  HIP70334 rather than a single source labelled `HIP70950_OFF`.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on HD 127506 b.
- The minimum empirical p-value measures departure from the circular-shift
  null. Strong matched and local control structure identifies non-unique
  features.
- The null result constrains only the frozen frequency windows, signal model,
  cadence, and measured sensitivity.

## Reproducibility

The public preregistration commit is
`1762a7672fdce24ef21031ca4050b17acb7c1b61`; the successful execution commit
is `5656dd7e9ce091964bc67fd540a5a1db79b84ddb`. The frozen configuration
SHA-256 is `7eba3bba8a29676e7f251c2a2fc74b03baec1a7e76d698349255019a9c20d563`.
The complete search record SHA-256 is
`3746bbcf33b345f4a42c0a5f22edd0c49d4f15787cd3536d71c61969f7bb0eac`.
`DATA_MANIFEST_M27.sha256` identifies all 30 reproducible extracts and
`RESULTS_MANIFEST_M27.sha256` identifies all nine published outputs. Extracted
telescope slices are not committed.

Publication workflow run `32725332075` independently revalidated the artifact
digest, all result hashes, the complete disposition accounting, and the frozen
execution provenance before publishing the full result payload as commit
`c5b1d20d8540fbcfff905e06b3791f590e71cdbb`.
