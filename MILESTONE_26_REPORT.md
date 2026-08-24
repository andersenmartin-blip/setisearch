# Milestone 26 report: HD 19994 held-out detector-v0.5 search

Status: **NO SURVIVING CANDIDATE; ALL 52 OVER-THRESHOLD CLUSTERS ARE VETOED AS OFF-SOURCE RFI**.

Milestone 26 applied frozen detector v0.5.0 to the sole complete compatible
GBT L-band HD 19994 cadence `--84358`. HD 19994 b supplies only the motion
template; the search does not assume that an emitter is located on the planet.

GitHub Actions run `32695770386` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9509135478`, named `milestone-26-held-out-results`, has verified digest
`sha256:b80b13b4c9975fb8214f905145cfa4cc6d0879ac41cac8dc614fdcc00237e009`.
All nine result files match `RESULTS_MANIFEST_M26.sha256`; the data manifest
contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Global result

Across approximately **592,487,280** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 644.919191** at 1406.437003620 MHz;
- scrambled-null median: **S/N 8.666516**;
- scrambled-null 99th percentile and operational threshold:
  **S/N 12.732759**;
- empirical global p-value: **1/257 = 0.00389105**; and
- final frozen disposition: **local OFF-source RFI; no survivor**.

At the maximum, the frozen local-OFF search finds S/N 514.422039 only
19.849 Hz away. The OFF global maximum reaches S/N 619.848320. The low
empirical rank therefore reflects strong structured interference in the local
field, not evidence of an astrophysical or artificial source.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p | Frozen maximum disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 5.551 | 1400.639285600 | 1 | 6.052 | 0.891051 | below threshold |
| 1406.0-1407.0 | 644.919 | 1406.437003620 | 9 | 619.848 | 0.003891 | local OFF source |
| 1412.0-1413.0 | 5.499 | 1412.847488111 | 1 | 5.540 | 0.953307 | below threshold |
| 1418.0-1419.0 | 6.391 | 1418.671876876 | 9 | 5.986 | 0.027237 | below global threshold |
| 1424.5-1425.5 | 10.099 | 1424.714300345 | 9 | 7.451 | 0.221790 | below global threshold |

Window p-values measure departure from the circular-shift null and do not
override the fixed global threshold or physical OFF-source evidence.

## Complete disposition accounting

The prospectively fixed 1200-cluster cap retained every one of the 353
clusters. **52** exceeded the global threshold, all in the 1406 MHz window:

| Physical disposition | 1406 MHz | Total |
|---|---:|---:|
| exact matched OFF-source recurrence | 21 | 21 |
| local OFF-source recurrence | 31 | 31 |
| **survivors** | **0** | **0** |

The remaining 301 clusters were below threshold. Receiver-frame-alias,
arithmetic-frequency-family, and widest-template flags provide additional
triage evidence, but every above-threshold rejection already satisfies a
frozen physical OFF-source criterion.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 0/32 (0%) | 0/32 (0%) |
| 12 | 1/32 (3.1%) | 1/32 (3.1%) |
| 16 | 17/32 (53.1%) | 14/32 (43.8%) |
| 20 | 31/32 (96.9%) | 22/32 (68.8%) |
| 24 | 32/32 (100%) | 23/32 (71.9%) |
| 32 | 32/32 (100%) | 25/32 (78.1%) |
| 40 | 32/32 (100%) | 28/32 (87.5%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **15.75** and **19.37**. The one-channel 50% estimate is
**17.00**; one-channel recovery does not reach 90% anywhere on the fixed grid
through S/N 40. These are grid interpolations, not confidence bounds.

## Independent-cadence boundary

The frozen screen contains no second qualifying HD 19994 L-band cadence;
`--63712` is S-band. No primary case survived the automatic physical vetoes,
so Milestone 26 closes as a primary-cadence null result. This archive selection
could not have established independent recurrence even if a case survived.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three ON scans belong to one approximately 32-minute cadence spanning
  2016-02-18 and 2016-02-19 UTC, not independent observing nights.
- All three controls use the archive source label `HIP14954_OFF`; they are the
  frozen OFF observations supplied by the cadence.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on HD 19994 b.
- The minimum empirical p-value measures departure from the circular-shift
  null. Strong matched and local OFF structure identifies non-unique local
  features.
- The null result constrains only the frozen frequency windows, signal model,
  cadence, and measured sensitivity.

## Reproducibility and fail-closed retry

The public preregistration commit is
`c4f0f977de0a39f2dcafa4b49ee201884707e6d4`; the successful execution commit
is `5513a61c168828eb6604555e93fae012228d7825`. The frozen configuration
SHA-256 is `4ae3587e7c75835e72298a22dffcb5887d711b0b7720977b6c1384e9277a6047`.
The complete search record SHA-256 is
`80f61010b440d112d57c288e475f9036e62e49f7b2d96883f3cfb34e72d7c8cf`.
`DATA_MANIFEST_M26.sha256` identifies all 30 reproducible extracts and
`RESULTS_MANIFEST_M26.sha256` identifies all nine published outputs. Extracted
telescope slices are not committed.

The first execution run `32695568295` stopped at provenance verification
before extraction because the initial Git-Data upload of the 325,711-byte
coverage JSON was incomplete. Commit
`f887e1f73408b4cfdb69d83e802f25e4cfd35142` restored the file byte-for-byte;
the correct SHA-256
`e8630f1275df3a3e1116a4a734c0666a387cdb9b3477cc0ad0e0cc5cb318dea9`
then matched its already-published manifest. No detector rule, configuration,
seed, input identity, or scientific datum changed during the retry.
