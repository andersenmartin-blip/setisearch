# Milestone 23 report: HD 33564 held-out detector-v0.5 search

Status: **NO SURVIVING CANDIDATE; ALL 77 OVER-THRESHOLD CLUSTERS ARE VETOED AS RFI OR INSTRUMENTAL**.

Milestone 23 applied frozen detector v0.5.0 to the earliest complete compatible
GBT L-band HD 33564 cadence `--71505`. HD 33564 b supplies only the motion
template; the search does not assume that an emitter is located on the planet.

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
  **S/N 7.945475**;
- empirical global p-value: **1/257 = 0.00389105**; and
- final frozen disposition: **matched OFF-source RFI; no survivor**.

The low empirical rank does not imply an astrophysical or artificial origin.
The global maximum is reproduced at the exact matched hypothesis in OFF data
at S/N 164.785674 and by the local OFF search at S/N 273.743719. The OFF
global maximum is stronger still, at S/N 339.148900.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p | Frozen maximum disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 184.273 | 1400.135544237 | 5 | 339.149 | 0.003891 | matched OFF source |
| 1406.0-1407.0 | 6.773 | 1406.642977425 | 9 | 6.473 | 0.007782 | below threshold |
| 1412.0-1413.0 | 5.882 | 1412.503178599 | 5 | 13.115 | 0.307393 | below threshold |
| 1418.0-1419.0 | 9.051 | 1418.949424459 | 3 | 72.376 | 0.003891 | local OFF source |
| 1424.5-1425.5 | 7.839 | 1425.216944368 | 9 | 7.628 | 0.003891 | below global threshold |

The window p-values measure departure from the circular-shift null. They do
not override the fixed physical OFF-source evidence.

## Complete disposition audit

The primary 1400 MHz output reached its preregistered 50-cluster report cap
while the 50th case remained above the global threshold. A post-hoc audit was
therefore frozen before re-extraction. Its sole configuration change increased
`max_report_clusters` from 50 to 500; all data identities, scores, thresholds,
vetoes, bands, templates, and seeds remained unchanged.

GitHub Actions run `32650710642` verified byte-identical hashes for all 30
primary extracts, reproduced every frozen primary maximum and null result, and
preserved all pre-limit clusters. Artifact `9496348803`, named
`milestone-23-complete-audit`, has verified digest
`sha256:6cdfc1eb059e1c12751de141e00abe93326e4329acfdb1dc8d0af1b57ef7bd96`.

| Window | Complete clusters | Above global threshold | Physical dispositions | Survivors |
|---|---:|---:|---|---:|
| 1400.0-1401.0 | 124 | 73 | 30 matched OFF; 39 local OFF; 3 receiver aliases; 1 single adjacent OFF | 0 |
| 1406.0-1407.0 | 32 | 0 | — | 0 |
| 1412.0-1413.0 | 7 | 0 | — | 0 |
| 1418.0-1419.0 | 12 | 4 | 1 matched OFF; 3 local OFF | 0 |
| 1424.5-1425.5 | 297 | 0 | — | 0 |

Across the complete audit, **77** clusters exceed the unchanged operational
threshold. All receive a frozen physical interference disposition. No
arithmetic-family-only or morphology-only case remains for post-hoc review.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 6/32 (18.8%) | 5/32 (15.6%) |
| 12 | 29/32 (90.6%) | 23/32 (71.9%) |
| 16 | 32/32 (100%) | 31/32 (96.9%) |
| 20 | 32/32 (100%) | 31/32 (96.9%) |
| 24 | 32/32 (100%) | 31/32 (96.9%) |
| 32 | 32/32 (100%) | 31/32 (96.9%) |
| 40 | 32/32 (100%) | 32/32 (100%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **9.74** and **11.97**. The corresponding one-channel
estimates are **10.44** and **14.90**. These are grid interpolations, not
confidence bounds; a 32/32 level has a Wilson 95% lower bound of 89.3%.

## Independent-cadence decision

The frozen header screen contains a second complete compatible HD 33564
L-band cadence, `--71747`, observed six days after the primary. The
preregistered rule allowed its spectral data to be opened only after a primary
case survived all automatic vetoes and a separately frozen morphology review.
No case survived, so the trigger did not fire. The independent cadence remains
spectrally untouched and is not used to strengthen the null result.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three searched ON scans belong to one approximately 28-minute cadence
  on 2016-05-18, not independent observing nights.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on HD 33564 b.
- The minimum empirical p-value measures departure from the circular-shift
  null. The frozen OFF and receiver-frame checks identify non-unique local
  features.
- The null result constrains only the frozen frequency windows, signal model,
  cadence, and measured sensitivity.

## Reproducibility

The public preregistration commit is
`4ddb99fe875e846bc012b40f68741a9f3b3d7e95`; the primary execution commit is
`10013ac24e047837de1a162402ee8db130e7582d`. The frozen primary configuration
SHA-256 is
`c36f73c812d4d863e059979573775aac20ef5a2ec38aafc30b9c2abe2629edf7`.
The separately frozen complete-audit configuration SHA-256 is
`0af0f6a23308fab5cc83a6bdef9f8e1a7a7e6ac2fc477ab96762a6ad68acb05b`.
The primary and audit data manifests identify byte-identical sets of 30
reproducible extracts; the corresponding result manifests identify all
published outputs. Extracted telescope slices are not committed.
