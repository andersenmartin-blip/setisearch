# Milestone 28 report: psi1 Dra B held-out detector-v0.5 search

Status: **NO SURVIVING CANDIDATE; ALL 196 OVER-THRESHOLD CLUSTERS ARE VETOED BY FROZEN CONTROL-SOURCE CRITERIA**.

Milestone 28 applied frozen detector v0.5.0 to the sole complete compatible
GBT L-band psi1 Dra B cadence `--84027`. psi1 Dra B b supplies only the motion
template; the search does not assume that an emitter is located on the planet.

GitHub Actions run `32752547391` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9530113650`, named `milestone-28-held-out-results`, has verified digest
`sha256:2315ef8e039bec232feccafe02ceb3f4c83e0a44bb8a7b2d319ebd6fee9d4024`.
All nine result files match `RESULTS_MANIFEST_M28.sha256`; the data manifest
contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Global result

Across approximately **592,487,280** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 184.854734** at 1400.052203120 MHz;
- scrambled-null median: **S/N 6.679100**;
- scrambled-null 99th percentile and operational threshold:
  **S/N 10.565890**;
- empirical global p-value: **1/257 = 0.00389105**; and
- final frozen disposition: **local control-source RFI; no survivor**.

At the maximum, the frozen local-control search finds S/N 159.774815 only
2.836 Hz away. The strongest control-source search reaches S/N 160.801494 in
the same 1400 MHz window. The low empirical rank therefore reflects strong,
structured interference shared with the alternating controls, not evidence
of an astrophysical or artificial source.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | control-global S/N | Empirical p | Frozen maximum disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 184.855 | 1400.052203120 | 1 | 160.801 | 0.003891 | local control source |
| 1406.0-1407.0 | 120.949 | 1406.331176961 | 9 | 105.360 | 0.003891 | local control source |
| 1412.0-1413.0 | 8.495 | 1412.524609334 | 9 | 10.772 | 0.003891 | below global threshold |
| 1418.0-1419.0 | 15.002 | 1418.994228249 | 5 | 14.251 | 0.003891 | single adjacent control |
| 1424.5-1425.5 | 30.506 | 1425.009155841 | 9 | 23.977 | 0.003891 | local control source |

Window p-values measure departure from the circular-shift null and do not
override the fixed global threshold or physical control-source evidence.

## Complete disposition accounting

The prospectively fixed 1200-cluster cap retained every one of the 296
clusters. **196** exceeded the global threshold:

| Physical disposition | 1400 MHz | 1406 MHz | 1412 MHz | 1418 MHz | 1425 MHz | Total |
|---|---:|---:|---:|---:|---:|---:|
| exact matched control-source recurrence | 30 | 21 | 0 | 8 | 3 | 62 |
| local control-source recurrence | 9 | 46 | 0 | 11 | 64 | 130 |
| single adjacent-control coincidence | 0 | 0 | 0 | 4 | 0 | 4 |
| **survivors** | **0** | **0** | **0** | **0** | **0** | **0** |

The remaining 100 clusters were below threshold. Receiver-frame-alias and
arithmetic-frequency-family flags provide additional triage evidence, but
every above-threshold rejection already satisfies a frozen physical
control-source criterion.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 0/32 (0.0%) | 0/32 (0.0%) |
| 12 | 12/32 (37.5%) | 11/32 (34.4%) |
| 16 | 29/32 (90.6%) | 23/32 (71.9%) |
| 20 | 32/32 (100%) | 26/32 (81.2%) |
| 24 | 32/32 (100%) | 28/32 (87.5%) |
| 32 | 32/32 (100%) | 29/32 (90.6%) |
| 40 | 32/32 (100%) | 29/32 (90.6%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **12.94** and **15.95**. The one-channel 50% and 90%
estimates are approximately **13.67** and **30.40**. These are grid
interpolations, not confidence bounds.

## Independent-cadence boundary

The frozen screen contains no second qualifying psi1 Dra B L-band cadence;
`--80213` is S-band. No primary case survived the automatic physical vetoes,
so Milestone 28 closes as a primary-cadence null result. This archive selection
could not have established independent recurrence even if a case survived.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three ON scans belong to one approximately 32-minute cadence on
  2016-01-18, not independent observing nights.
- The three alternating controls use the archive source label
  `HIP86620_OFF`; they are control pointings, not independent target epochs.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on psi1 Dra B b.
- The minimum empirical p-value measures departure from the circular-shift
  null. Strong matched and local control structure identifies non-unique
  features.
- The null result constrains only the frozen frequency windows, signal model,
  cadence, and measured sensitivity.

## Reproducibility

The public preregistration commit is
`0e7a4bea59819b26d2b8a16375a43e40f836d27e`; the successful execution commit
is `4a1727e305b9db61eb8d169882f536f4af258f81`. The frozen configuration
SHA-256 is `a0c118cf0589d1edd23b550574dd22a5cfad1f8db9a3d5507aa4437085b16e79`.
The complete search record SHA-256 is
`68225e98363a5b8508702faa25c207866e9977d1385e81b1015318f51dcd77c1`.
`DATA_MANIFEST_M28.sha256` identifies all 30 reproducible extracts and
`RESULTS_MANIFEST_M28.sha256` identifies all nine published outputs. Extracted
telescope slices are not committed.

Publication verification is appended after the independent verification
workflow has revalidated the hashes, disposition accounting, execution
provenance, and this report.
