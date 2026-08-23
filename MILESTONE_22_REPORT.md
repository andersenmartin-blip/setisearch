# Milestone 22 report: HD 87883 held-out detector-v0.5 search

Status: **NO SURVIVING CANDIDATE; ALL 20 OVER-THRESHOLD CASES ARE VETOED AS RFI OR INSTRUMENTAL**.

Milestone 22 applied frozen detector v0.5.0 to the sole complete compatible
GBT L-band HD 87883 cadence `--70933`. HD 87883 b supplies only the motion
template; the search does not assume that an emitter is located on the planet.

GitHub Actions run `32640562149` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9493695805`, named `milestone-22-held-out-results`, has verified digest
`sha256:ec39fa4b24a9eea910c2865eff165c39495257b2377d1d7d4594ef986f227791`.
All nine primary result files match `RESULTS_MANIFEST_M22.sha256`; the data
manifest contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Global result

Across approximately **592,487,280** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 16.111804** at 1400.114068134 MHz;
- scrambled-null median: **S/N 6.421316**;
- scrambled-null 99th percentile and operational threshold:
  **S/N 8.364511**;
- empirical global p-value: **1/257 = 0.00389105**; and
- final frozen disposition: **receiver-frame alias; no survivor**.

The low empirical rank does not imply an astrophysical or artificial origin.
The maximum is one of 20 over-threshold planet-frame clusters in the 1400 MHz
window. Nineteen, including the maximum, map to the same recorded receiver
feature in both active ON epochs and receive the frozen
`rfi_veto_receiver_frame_alias` disposition. The remaining case is reproduced
locally in OFF-source data and receives `rfi_veto_local_off_source`.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p | Frozen maximum disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 16.112 | 1400.114068134 | 9 | 14.651 | 0.003891 | receiver-frame alias |
| 1406.0-1407.0 | 5.455 | 1406.839438116 | 1 | 5.942 | 0.848249 | below threshold |
| 1412.0-1413.0 | 5.685 | 1412.586604775 | 9 | 5.536 | 0.552529 | below threshold |
| 1418.0-1419.0 | 5.797 | 1418.524396672 | 5 | 5.618 | 0.299611 | below threshold |
| 1424.5-1425.5 | 7.383 | 1425.467807028 | 9 | 7.329 | 0.027237 | below threshold |

The window p-values measure departure from the circular-shift null. They do
not override the fixed physical receiver-frame and OFF-source evidence.

## Candidate reduction and physical vetoes

The frozen procedure retained 591 hypothesis peaks, formed 345 frequency
clusters before report limits, and reported 109 clusters:

- 19 receiver-frame-alias vetoes;
- 1 local-OFF veto; and
- 89 below threshold.

The global maximum and its 19 receiver-alias partners select the same measured
features at **1399.996847298 MHz** in active epoch 1 and
**1399.996818943 MHz** in active epoch 2. For the maximum those local feature
strengths are S/N 18.564 and 14.119. The 19 other planet-frame solutions agree
with those same receiver frequencies to 0.0 Hz in both epochs, satisfying the
frozen two-epoch alias rule.

The sole remaining over-threshold cluster is at **1400.119478274 MHz** with
S/N 15.693751. A local OFF-source search finds S/N 8.706962 only 19.849 Hz
away, within the preregistered 20 Hz tolerance. It therefore independently
receives the fixed local-OFF veto. No arithmetic-family-only or morphology-only
case remains for post-hoc review.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 4/32 (12.5%) | 4/32 (12.5%) |
| 12 | 26/32 (81.3%) | 21/32 (65.6%) |
| 16 | 32/32 (100%) | 30/32 (93.8%) |
| 20 | 32/32 (100%) | 31/32 (96.9%) |
| 24 | 32/32 (100%) | 31/32 (96.9%) |
| 32 | 32/32 (100%) | 31/32 (96.9%) |
| 40 | 32/32 (100%) | 31/32 (96.9%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **10.18** and **13.87**. The corresponding one-channel
estimates are **10.82** and **15.47**. These are grid interpolations, not
confidence bounds; a 32/32 level has a Wilson 95% lower bound of 89.3%.

## Follow-up decision

The frozen protocol allowed a separately preregistered within-cadence
morphology review only if a case survived the global threshold and automatic
physical vetoes. None did, so that trigger did not fire. The other frozen HD
87883 cadence is S-band and does not cover these windows. Milestone 22
therefore closes at the primary no-survivor result.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three ON scans belong to one approximately 29-minute cadence on
  2016-05-13, not independent observing nights.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on HD 87883 b.
- The minimum empirical p-value measures departure from the circular-shift
  null. The frozen cross-template and OFF checks identify non-unique receiver
  features.
- The null result constrains only the frozen frequency windows, signal model,
  cadence, and measured sensitivity.

## Reproducibility

The public preregistration is commit
`083f5ee929c1abfa7d983f0213ce9b2d6e90afe7`; the execution commit is
`63b105eafc3af5c24c7485c1139f1a70c70ad2ee`. The frozen configuration
SHA-256 is
`13870d7dd9b65bed2fc520211e701134bf4a7b9f9b19aa29e017fe3722430e49`.
`DATA_MANIFEST_M22.sha256` identifies the 30 reproducible extracts;
`RESULTS_MANIFEST_M22.sha256` identifies all primary outputs. Extracted
telescope slices are not committed.
